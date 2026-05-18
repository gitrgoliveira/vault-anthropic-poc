#!/usr/bin/env python3
"""
End-to-end test: Vault AppRole → SPIFFE JWT-SVID → Anthropic WIF token exchange → Claude API call.

Prerequisites:
  - Terraform has been applied (Vault SPIFFE secrets engine configured).
  - Anthropic Console has issuer, service account, and federation rule configured.
  - Environment variables set (see below).

Required environment variables:
  VAULT_ADDR                     - HCP Vault address
  VAULT_NAMESPACE                - Vault namespace (default: admin)
  VAULT_APPROLE_ROLE_ID          - AppRole role ID from Terraform output
  VAULT_APPROLE_SECRET_ID        - AppRole secret ID (generate via vault write -f auth/approle/role/<name>/secret-id)
  VAULT_SPIFFE_ROLE              - SPIFFE role name (for example, research-workload)
  ANTHROPIC_ORGANIZATION_ID      - Anthropic org UUID
  ANTHROPIC_FEDERATION_RULE_ID   - Federation rule ID (fdrl_...)
  ANTHROPIC_SERVICE_ACCOUNT_ID   - Service account ID (svac_...)
"""

import base64
import json
import os
import sys

import hvac


def decode_jwt_payload(token: str) -> dict:
    """Decode a JWT payload without verification (for display only)."""
    parts = token.split(".")
    if len(parts) != 3:
        return {"error": "invalid JWT format"}
    payload = parts[1]
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding
    return json.loads(base64.urlsafe_b64decode(payload))


def extract_spiffe_token(response: dict | None) -> str:
    """Handle the response shape from the SPIFFE mint endpoint defensively."""
    if not response:
        raise KeyError("empty response from SPIFFE mint endpoint")
    data = response.get("data", {})
    token = data.get("token") or data.get("svid") or data.get("jwt") or response.get("token")
    if not token:
        raise KeyError(f"could not find JWT token in response keys: {list(data.keys())}")
    return token


def main():
    vault_addr = os.environ.get("VAULT_ADDR")
    vault_namespace = os.environ.get("VAULT_NAMESPACE", "admin")
    role_id = os.environ.get("VAULT_APPROLE_ROLE_ID")
    secret_id = os.environ.get("VAULT_APPROLE_SECRET_ID")
    spiffe_role = os.environ.get("VAULT_SPIFFE_ROLE")

    anthropic_org_id = os.environ.get("ANTHROPIC_ORGANIZATION_ID")
    federation_rule_id = os.environ.get("ANTHROPIC_FEDERATION_RULE_ID")
    service_account_id = os.environ.get("ANTHROPIC_SERVICE_ACCOUNT_ID")
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID")

    required = {
        "VAULT_ADDR": vault_addr,
        "VAULT_APPROLE_ROLE_ID": role_id,
        "VAULT_APPROLE_SECRET_ID": secret_id,
        "VAULT_SPIFFE_ROLE": spiffe_role,
        "ANTHROPIC_ORGANIZATION_ID": anthropic_org_id,
        "ANTHROPIC_FEDERATION_RULE_ID": federation_rule_id,
        "ANTHROPIC_SERVICE_ACCOUNT_ID": service_account_id,
    }

    missing = [k for k, v in required.items() if not v]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    print(f"[1/4] Authenticating to Vault at {vault_addr} (namespace: {vault_namespace})...")
    client = hvac.Client(url=vault_addr, namespace=vault_namespace)
    try:
        client.auth.approle.login(role_id=role_id, secret_id=secret_id)
    except Exception as e:
        print(f"ERROR: Vault AppRole login failed: {e}", file=sys.stderr)
        print("  Check that VAULT_APPROLE_ROLE_ID and VAULT_APPROLE_SECRET_ID are correct.", file=sys.stderr)
        print("  Secret IDs are single-use. Generate a fresh one with: make secret-id", file=sys.stderr)
        sys.exit(1)

    if not client.is_authenticated():
        print("ERROR: Vault authentication failed.", file=sys.stderr)
        sys.exit(1)
    print("       Vault authentication successful.")

    print(f"[2/4] Minting SPIFFE JWT-SVID from spiffe/role/{spiffe_role}/mintjwt...")
    try:
        response = client.write(f"spiffe/role/{spiffe_role}/mintjwt", audience="https://api.anthropic.com")
        jwt_token = extract_spiffe_token(response)
    except Exception as e:
        print(f"ERROR: Failed to mint SPIFFE JWT-SVID: {e}", file=sys.stderr)
        print(f"  Path: spiffe/role/{spiffe_role}/mintjwt", file=sys.stderr)
        print("  Check that the SPIFFE role exists and the policy grants create/update access.", file=sys.stderr)
        sys.exit(1)

    claims = decode_jwt_payload(jwt_token)
    print("       JWT-SVID minted. Claims:")
    print(f"         iss: {claims.get('iss')}")
    print(f"         sub: {claims.get('sub')}")
    print(f"         aud: {claims.get('aud')}")
    print(f"         environment: {claims.get('environment')}")
    print(f"         team: {claims.get('team')}")
    print(f"         entity_id: {claims.get('entity_id')}")
    print(f"         exp: {claims.get('exp')}")

    print("[3/4] Configuring Anthropic federation environment...")
    os.environ["ANTHROPIC_IDENTITY_TOKEN"] = jwt_token
    os.environ["ANTHROPIC_ORGANIZATION_ID"] = anthropic_org_id
    os.environ["ANTHROPIC_FEDERATION_RULE_ID"] = federation_rule_id
    os.environ["ANTHROPIC_SERVICE_ACCOUNT_ID"] = service_account_id
    if workspace_id:
        os.environ["ANTHROPIC_WORKSPACE_ID"] = workspace_id

    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

    print(f"       ANTHROPIC_FEDERATION_RULE_ID = {federation_rule_id}")
    print(f"       ANTHROPIC_SERVICE_ACCOUNT_ID = {service_account_id}")
    if workspace_id:
        print(f"       ANTHROPIC_WORKSPACE_ID = {workspace_id}")

    print("[4/4] Calling Anthropic Messages API via federated token...")

    import anthropic

    anthropic_client = anthropic.Anthropic()
    try:
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Hello from Vault SPIFFE federation!' and nothing else.",
                }
            ],
        )
    except anthropic.AuthenticationError as e:
        print(f"\nERROR: Anthropic authentication failed: {e}", file=sys.stderr)
        print("  The JWT-SVID was minted but the token exchange failed.", file=sys.stderr)
        print("  Check that the federation rule's subject prefix and audience match your JWT-SVID.", file=sys.stderr)
        print(f"  Federation rule: {federation_rule_id}", file=sys.stderr)
        print(f"  Service account: {service_account_id}", file=sys.stderr)
        sys.exit(1)
    except anthropic.APIError as e:
        print(f"\nERROR: Anthropic API call failed: {e}", file=sys.stderr)
        sys.exit(1)

    print()
    print("=" * 60)
    print("SUCCESS - Federated authentication worked!")
    print("=" * 60)
    print(f"Model:    {message.model}")
    print(f"Response: {message.content[0].text}")
    print(f"Usage:    {message.usage.input_tokens} input, {message.usage.output_tokens} output tokens")
    print("=" * 60)


if __name__ == "__main__":
    main()
