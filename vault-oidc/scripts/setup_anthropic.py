#!/usr/bin/env python3
"""
Interactive setup wizard for Anthropic Console WIF configuration.

Reads Terraform outputs, walks you through the Console steps with
copy-paste values, prompts for the IDs that the Console generates,
validates them, and writes an .env file for the test script.
"""

import json
import os
import re
import subprocess
import sys
import webbrowser

CONSOLE_URL = "https://console.anthropic.com"
ENV_FILE = os.path.join(os.path.dirname(__file__), "..", ".env")

# Regex patterns for Anthropic resource IDs
RE_ORG_ID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)
RE_SVAC_ID = re.compile(r"^svac_[A-Za-z0-9_-]+$")
RE_FDRL_ID = re.compile(r"^fdrl_[A-Za-z0-9_-]+$")
RE_WRKSPC_ID = re.compile(r"^wrkspc_[A-Za-z0-9_-]+$")

# ANSI helpers
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"
DIM = "\033[2m"


def banner(msg: str) -> None:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  {msg}{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")


def step(num: int | str, title: str) -> None:
    print(f"\n{CYAN}{BOLD}── Step {num}: {title} ──{RESET}\n")


def copyable(label: str, value: str) -> None:
    print(f"  {DIM}{label}:{RESET}  {GREEN}{value}{RESET}")


def prompt_id(label: str, pattern: re.Pattern, hint: str) -> str:
    while True:
        value = input(f"  {YELLOW}▸{RESET} {label} ({hint}): ").strip()
        if pattern.match(value):
            return value
        print(f"  {RED}✗ Invalid format. Expected: {hint}{RESET}")


def prompt_yn(msg: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"  {msg} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer.startswith("y")


def terraform_output(name: str, *, raw: bool = False) -> str:
    cmd = ["terraform", "output"]
    if raw:
        cmd += ["-raw", name]
    else:
        cmd += ["-json", name]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"{RED}ERROR: terraform output {name} failed:{RESET}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout.strip()


def terraform_outputs() -> dict:
    """Gather all needed values from Terraform state."""
    issuer_url = terraform_output("oidc_issuer_url", raw=True)
    discovery_url = terraform_output("oidc_discovery_url", raw=True)
    jwks_url = terraform_output("oidc_jwks_url", raw=True)
    audience = terraform_output("anthropic_audience", raw=True)
    environments = json.loads(terraform_output("oidc_role_names"))
    role_ids = json.loads(terraform_output("approle_role_ids"))
    environment_configs = json.loads(terraform_output("environment_configs"))
    return {
        "issuer_url": issuer_url,
        "discovery_url": discovery_url,
        "jwks_url": jwks_url,
        "audience": audience,
        "environments": environments,
        "role_ids": role_ids,
        "environment_configs": environment_configs,
    }


def check_oidc_discovery(discovery_url: str) -> bool:
    """Quick check that the OIDC discovery endpoint is reachable."""
    try:
        result = subprocess.run(
            ["curl", "-sSf", discovery_url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"  {RED}curl failed (exit {result.returncode}): {result.stderr.strip()}{RESET}")
            return False
        doc = json.loads(result.stdout)
        return "jwks_uri" in doc
    except subprocess.TimeoutExpired:
        print(f"  {RED}curl timed out after 30s{RESET}")
    except json.JSONDecodeError as e:
        print(f"  {RED}Invalid JSON from discovery endpoint: {e}{RESET}")
    except Exception as e:
        print(f"  {RED}Unexpected error: {e}{RESET}")
    return False


def fetch_jwks_keys(jwks_url: str) -> list | None:
    """Fetch JWKS keys array from Vault for inline mode."""
    try:
        result = subprocess.run(
            ["curl", "-sSf", jwks_url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"  {RED}curl failed (exit {result.returncode}): {result.stderr.strip()}{RESET}")
            return None
        jwks = json.loads(result.stdout)
        return jwks.get("keys", [])
    except subprocess.TimeoutExpired:
        print(f"  {RED}curl timed out after 30s{RESET}")
    except json.JSONDecodeError as e:
        print(f"  {RED}Invalid JSON from JWKS endpoint: {e}{RESET}")
    except Exception as e:
        print(f"  {RED}Unexpected error: {e}{RESET}")
    return None


def issuer_needs_inline(issuer_url: str) -> bool:
    """Return True if the issuer URL uses a non-443 port (requires inline JWKS)."""
    from urllib.parse import urlparse
    parsed = urlparse(issuer_url)
    port = parsed.port
    # No explicit port means default 443 for https
    return port is not None and port != 443


def build_env_config(environment_configs: dict) -> dict:
    """Build environment configuration from Terraform outputs."""
    config = {}
    for key, env in environment_configs.items():
        env_label = env["environment"].capitalize()
        config[key] = {
            "sa_name": f"{key}-worker",
            "sa_desc": f"{env_label} environment workloads",
            "rule_name": f"{key}-rule",
            "rule_desc": f"{env_label} environment federation rule",
            "condition": (
                f'claims.metadata.environment == "{env["environment"]}"'
                f' && "{env["group_name"]}" in claims.groups'
            ),
        }
    return config


def write_env_file(org_id: str, env_ids: dict, workspace_id: str | None = None) -> str:
    """Write .env file with all collected IDs."""
    lines = [
        "# Generated by scripts/setup_anthropic.py",
        "# Source this file before running the test:",
        "#   source .env && make test ENV=research",
        "",
        f"export ANTHROPIC_ORGANIZATION_ID={org_id}",
    ]
    if workspace_id:
        lines.append(f"export ANTHROPIC_WORKSPACE_ID={workspace_id}")
    lines.append("")
    for env_key, ids in env_ids.items():
        lines.append(f"# {env_key}")
        lines.append(f"export ANTHROPIC_{env_key.upper()}_FEDERATION_RULE_ID={ids['rule_id']}")
        lines.append(f"export ANTHROPIC_{env_key.upper()}_SERVICE_ACCOUNT_ID={ids['sa_id']}")
        lines.append("")

    # Write a convenience function that picks the right IDs based on $ENV
    # Uses POSIX-compatible syntax (works in bash, zsh, dash)
    lines.extend([
        "# Convenience: set ANTHROPIC_FEDERATION_RULE_ID and ANTHROPIC_SERVICE_ACCOUNT_ID",
        "# based on the ENV variable (default: research).",
        '# Usage: source .env && eval "$(_anthropic_env research)" && make test ENV=research',
        "_anthropic_env() {",
        '  _ae_env="${1:-research}"',
        "  _ae_upper=\"$(printf '%s' \"$_ae_env\" | tr '[:lower:]' '[:upper:]')\"",
        '  eval "echo \\"export ANTHROPIC_FEDERATION_RULE_ID=\\$ANTHROPIC_${_ae_upper}_FEDERATION_RULE_ID\\""',
        '  eval "echo \\"export ANTHROPIC_SERVICE_ACCOUNT_ID=\\$ANTHROPIC_${_ae_upper}_SERVICE_ACCOUNT_ID\\""',
        "}",
        "",
    ])

    env_path = os.path.abspath(ENV_FILE)
    with open(env_path, "w") as f:
        f.write("\n".join(lines))
    os.chmod(env_path, 0o600)
    return env_path


def main():
    banner("Anthropic Console Setup Wizard")
    print("This script walks you through the manual Console steps,")
    print("provides exact copy-paste values, and collects the IDs")
    print("the Console generates so you can run the test script.\n")

    # ── Pre-flight: read Terraform outputs ──────────────────────────
    print(f"{DIM}Reading Terraform outputs...{RESET}")
    tf = terraform_outputs()
    env_config = build_env_config(tf["environment_configs"])
    print(f"{GREEN}✓{RESET} Terraform outputs loaded.\n")

    # ── Pre-flight: detect inline vs discovery mode ─────────────────
    use_inline = issuer_needs_inline(tf["issuer_url"])
    jwks_keys_json = None

    if use_inline:
        print(f"{YELLOW}⚠  Vault issuer URL uses a non-443 port.{RESET}")
        print(f"   Anthropic requires port 443 for discovery mode.")
        print(f"   Will use {BOLD}inline JWKS{RESET} mode instead.\n")
        print(f"{DIM}Fetching JWKS keys from Vault...{RESET}")
        keys = fetch_jwks_keys(tf["jwks_url"])
        if keys:
            jwks_keys_json = json.dumps(keys, indent=2)
            print(f"{GREEN}✓{RESET} Fetched {len(keys)} signing key(s) from Vault.\n")
        else:
            print(f"{RED}✗ Could not fetch JWKS from {tf['jwks_url']}{RESET}")
            print("  Make sure Vault is running and 'terraform apply' succeeded.\n")
            if not prompt_yn("Continue anyway?", default=False):
                sys.exit(1)
    else:
        print(f"{DIM}Checking OIDC discovery endpoint...{RESET}")
        if check_oidc_discovery(tf["discovery_url"]):
            print(f"{GREEN}✓{RESET} OIDC discovery is reachable and valid.\n")
        else:
            print(f"{YELLOW}⚠  OIDC discovery check failed.{RESET}")
            print(f"   URL: {tf['discovery_url']}")
            print("   Make sure Vault is running and 'terraform apply' succeeded.\n")
            if not prompt_yn("Continue anyway?", default=False):
                sys.exit(1)

    # ── Step 0: Organization ID ─────────────────────────────────────
    step(0, "Organization ID")
    print("  Find your Organization ID in the Claude Console:")
    print(f"  {DIM}Settings → Organization → copy the UUID{RESET}\n")

    if prompt_yn("Open Console in browser?"):
        webbrowser.open(f"{CONSOLE_URL}/settings/organization")

    org_id = prompt_id("Organization ID", RE_ORG_ID, "UUID like 12345678-abcd-...")

    # ── Step 1: Register a federation issuer ────────────────────────
    step(1, "Register a Federation Issuer")
    print("  Create an issuer in the Claude Console:")
    print(f"  {DIM}Settings → Workload identity → Issuers tab → Create issuer{RESET}\n")
    print("  Use these exact values:\n")
    copyable("Name", "hcp-vault")
    copyable("Issuer URL", tf["issuer_url"])

    if use_inline:
        copyable("JWKS source", "inline")
        print()
        if jwks_keys_json:
            print(f"  Paste this into the {BOLD}Inline keys{RESET} field:\n")
            for line in jwks_keys_json.splitlines():
                print(f"    {GREEN}{line}{RESET}")
            print()
            print(f"  {DIM}(These are Vault's current public signing keys.")
            print(f"   If Vault rotates keys, re-run this script to get fresh ones.){RESET}")
        else:
            print(f"  {YELLOW}Could not auto-fetch keys. Manually copy from:{RESET}")
            print(f"  curl -s {tf['jwks_url']} | jq .keys")
    else:
        copyable("JWKS source", "discovery")
    print()

    if prompt_yn("Open Console in browser?"):
        webbrowser.open(f"{CONSOLE_URL}/settings/workload-identity-federation")

    input(f"\n  {YELLOW}▸{RESET} Press Enter when the issuer is created...")
    print(f"  {GREEN}✓{RESET} Issuer registered.\n")

    # ── Step 2: Create service accounts ─────────────────────────────
    step(2, "Create Service Accounts")
    print("  Create one service account per environment:")
    print(f"  {DIM}Settings → Service accounts → Create service account{RESET}\n")

    env_ids = {}
    for env_key, cfg in env_config.items():
        print(f"  {BOLD}» {env_key}{RESET}")
        copyable("Name", cfg["sa_name"])
        copyable("Description", cfg["sa_desc"])
        print()

    print("  After creating all three, add each to its workspace\n"
          "  from that workspace's Members page.\n")

    if prompt_yn("Open Console in browser?"):
        webbrowser.open(f"{CONSOLE_URL}/settings/service-accounts")

    print()
    for env_key, cfg in env_config.items():
        sa_id = prompt_id(
            f"{cfg['sa_name']} service account ID",
            RE_SVAC_ID,
            "svac_...",
        )
        env_ids[env_key] = {"sa_id": sa_id}

    print(f"\n  {GREEN}✓{RESET} Service accounts collected.\n")

    # ── Step 3: Create federation rules ─────────────────────────────
    step(3, "Create Federation Rules")
    print("  Create one rule per environment:")
    print(f"  {DIM}Settings → Workload identity → Federation rules tab → Create rule{RESET}\n")

    for env_key, cfg in env_config.items():
        print(f"  {BOLD}» {cfg['rule_name']}{RESET}")
        copyable("Name", cfg["rule_name"])
        copyable("Description", cfg["rule_desc"])
        copyable("Issuer", "hcp-vault")
        copyable("Match type", "CEL")
        copyable("Audience", tf["audience"])
        copyable("Condition", cfg["condition"])
        copyable("Target", f"{cfg['sa_name']} service account")
        copyable("OAuth scope", "workspace:developer")
        copyable("Token lifetime", "3600")
        print()

    if prompt_yn("Open Console in browser?"):
        webbrowser.open(f"{CONSOLE_URL}/settings/workload-identity-federation")

    print()
    for env_key, cfg in env_config.items():
        rule_id = prompt_id(
            f"{cfg['rule_name']} federation rule ID",
            RE_FDRL_ID,
            "fdrl_...",
        )
        env_ids[env_key]["rule_id"] = rule_id

    print(f"\n  {GREEN}✓{RESET} Federation rules collected.\n")

    # ── Step 3b: Workspace ID ───────────────────────────────────────
    step("3b", "Workspace ID")
    print("  If the service account is a member of multiple workspaces,")
    print("  you must specify which workspace to scope tokens to.")
    print()
    print(f"  {YELLOW}Important:{RESET} The service account must be a member of the workspace")
    print(f"  you specify. To add it: Console → Settings → Workspaces →")
    print(f"  select workspace → Members → Add to Workspace.")
    print()
    print(f"  {DIM}Find the workspace ID in Settings → Workspaces → click the workspace → copy the ID{RESET}\n")

    if prompt_yn("Do the service accounts belong to multiple workspaces?"):
        workspace_id = prompt_id("Workspace ID", RE_WRKSPC_ID, "wrkspc_...")
    else:
        workspace_id = None
        print(f"  {DIM}Skipping — single workspace, not required.{RESET}")

    # ── Step 4: Write .env ──────────────────────────────────────────
    step(4, "Write .env File")
    env_path = write_env_file(org_id, env_ids, workspace_id=workspace_id)
    print(f"  {GREEN}✓{RESET} Wrote {env_path}")
    print(f"  {DIM}(file permissions set to 0600 — contains sensitive IDs){RESET}\n")

    # ── Summary ─────────────────────────────────────────────────────
    banner("Setup Complete!")

    print("  To run the federation test:\n")
    print(f"  {CYAN}source .env{RESET}")
    print(f"  {CYAN}make secret-id ENV=research{RESET}")
    print(f"  {CYAN}export VAULT_APPROLE_SECRET_ID=<secret_id from make secret-id>{RESET}")
    print(f"  {CYAN}export ANTHROPIC_FEDERATION_RULE_ID=$ANTHROPIC_RESEARCH_FEDERATION_RULE_ID{RESET}")
    print(f"  {CYAN}export ANTHROPIC_SERVICE_ACCOUNT_ID=$ANTHROPIC_RESEARCH_SERVICE_ACCOUNT_ID{RESET}")
    if workspace_id:
        print(f"  {DIM}(ANTHROPIC_WORKSPACE_ID is already set in .env){RESET}")
    print(f"  {CYAN}make test ENV=research{RESET}")
    print()


if __name__ == "__main__":
    main()
