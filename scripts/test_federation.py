#!/usr/bin/env python3
"""
End-to-end test: Vault AppRole → OIDC JWT → Anthropic WIF token exchange → Claude API call.

Prerequisites:
  - Terraform has been applied (Vault OIDC provider configured).
  - Anthropic Console has issuer, service account, and federation rule configured.
  - Environment variables set (see below).

Required environment variables:
  VAULT_ADDR                     - HCP Vault address
  VAULT_NAMESPACE                - Vault namespace (default: admin)
  VAULT_APPROLE_ROLE_ID          - AppRole role ID from Terraform output
  VAULT_APPROLE_SECRET_ID        - AppRole secret ID (generate via vault write -f auth/approle/role/<name>/secret-id)
  VAULT_OIDC_ROLE                - OIDC role name (e.g. anthropic-research-role)
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
    # Add padding
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding
    return json.loads(base64.urlsafe_b64decode(payload))


def main():
    # -------------------------------------------------------------------------
    # 1. Read configuration from environment
    # -------------------------------------------------------------------------
    vault_addr = os.environ.get("VAULT_ADDR")
    vault_namespace = os.environ.get("VAULT_NAMESPACE", "admin")
    role_id = os.environ.get("VAULT_APPROLE_ROLE_ID")
    secret_id = os.environ.get("VAULT_APPROLE_SECRET_ID")
    oidc_role = os.environ.get("VAULT_OIDC_ROLE")

    anthropic_org_id = os.environ.get("ANTHROPIC_ORGANIZATION_ID")
    federation_rule_id = os.environ.get("ANTHROPIC_FEDERATION_RULE_ID")
    service_account_id = os.environ.get("ANTHROPIC_SERVICE_ACCOUNT_ID")
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID")

    required = {
        "VAULT_ADDR": vault_addr,
        "VAULT_APPROLE_ROLE_ID": role_id,
        "VAULT_APPROLE_SECRET_ID": secret_id,
        "VAULT_OIDC_ROLE": oidc_role,
        "ANTHROPIC_ORGANIZATION_ID": anthropic_org_id,
        "ANTHROPIC_FEDERATION_RULE_ID": federation_rule_id,
        "ANTHROPIC_SERVICE_ACCOUNT_ID": service_account_id,
    }

    missing = [k for k, v in required.items() if not v]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # -------------------------------------------------------------------------
    # 2. Authenticate to Vault via AppRole
    # -------------------------------------------------------------------------
    print(f"[1/4] Authenticating to Vault at {vault_addr} (namespace: {vault_namespace})...")
    client = hvac.Client(url=vault_addr, namespace=vault_namespace)
    try:
        client.auth.approle.login(role_id=role_id, secret_id=secret_id)
    except Exception as e:
        print(f"ERROR: Vault AppRole login failed: {e}", file=sys.stderr)
        print("  Check that VAULT_APPROLE_ROLE_ID and VAULT_APPROLE_SECRET_ID are correct.", file=sys.stderr)
        print("  Secret IDs are single-use — generate a fresh one with: make secret-id", file=sys.stderr)
        sys.exit(1)

    if not client.is_authenticated():
        print("ERROR: Vault authentication failed.", file=sys.stderr)
        sys.exit(1)
    print("       Vault authentication successful.")

    # -------------------------------------------------------------------------
    # 3. Read an OIDC token from Vault
    # -------------------------------------------------------------------------
    print(f"[2/4] Reading OIDC token from identity/oidc/token/{oidc_role}...")
    try:
        response = client.read(f"identity/oidc/token/{oidc_role}")
        jwt_token = response["data"]["token"]
    except Exception as e:
        print(f"ERROR: Failed to read OIDC token: {e}", file=sys.stderr)
        print(f"  Path: identity/oidc/token/{oidc_role}", file=sys.stderr)
        print("  Check that the OIDC role exists and the policy grants read access.", file=sys.stderr)
        sys.exit(1)

    claims = decode_jwt_payload(jwt_token)
    print(f"       Token minted. Claims:")
    print(f"         iss: {claims.get('iss')}")
    print(f"         sub: {claims.get('sub')}")
    print(f"         aud: {claims.get('aud')}")
    metadata = claims.get("metadata", {})
    print(f"         metadata.environment: {metadata.get('environment')}")
    print(f"         metadata.team: {metadata.get('team')}")
    print(f"         groups: {claims.get('groups')}")
    print(f"         exp: {claims.get('exp')}")

    # -------------------------------------------------------------------------
    # 4. Write JWT to a temp file and configure Anthropic SDK env vars
    # -------------------------------------------------------------------------
    print("[3/4] Configuring Anthropic federation environment...")
    os.environ["ANTHROPIC_IDENTITY_TOKEN"] = jwt_token
    os.environ["ANTHROPIC_ORGANIZATION_ID"] = anthropic_org_id
    os.environ["ANTHROPIC_FEDERATION_RULE_ID"] = federation_rule_id
    os.environ["ANTHROPIC_SERVICE_ACCOUNT_ID"] = service_account_id
    if workspace_id:
        os.environ["ANTHROPIC_WORKSPACE_ID"] = workspace_id

    # Ensure no API key shadows federation
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

    print(f"       ANTHROPIC_FEDERATION_RULE_ID = {federation_rule_id}")
    print(f"       ANTHROPIC_SERVICE_ACCOUNT_ID = {service_account_id}")
    if workspace_id:
        print(f"       ANTHROPIC_WORKSPACE_ID = {workspace_id}")

    # -------------------------------------------------------------------------
    # 5. Call the Anthropic Messages API via federation
    # -------------------------------------------------------------------------
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
                    "content": "Say 'Hello from Vault OIDC federation!' and nothing else.",
                }
            ],
        )
    except anthropic.AuthenticationError as e:
        print(f"\nERROR: Anthropic authentication failed: {e}", file=sys.stderr)
        print("  The JWT was minted but the token exchange failed.", file=sys.stderr)
        print("  Check that the federation rule's CEL condition matches your JWT claims.", file=sys.stderr)
        print(f"  Federation rule: {federation_rule_id}", file=sys.stderr)
        print(f"  Service account: {service_account_id}", file=sys.stderr)
        sys.exit(1)
    except anthropic.APIError as e:
        print(f"\nERROR: Anthropic API call failed: {e}", file=sys.stderr)
        sys.exit(1)

    print()
    print("=" * 60)
    print("SUCCESS — Federated authentication worked!")
    print("=" * 60)
    print(f"Model:    {message.model}")
    print(f"Response: {message.content[0].text}")
    print(f"Usage:    {message.usage.input_tokens} input, {message.usage.output_tokens} output tokens")
    print("=" * 60)


if __name__ == "__main__":
    main()
