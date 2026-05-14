# Vault OIDC → Anthropic Workload Identity Federation

> Companion repository for the blog post [Secure AI workloads with Vault OIDC and Anthropic federation]().

Replace static `sk-ant-...` API keys with ephemeral, identity-bound tokens by configuring HashiCorp Vault as an OIDC issuer for [Anthropic Workload Identity Federation](https://platform.claude.com/docs/en/manage-claude/workload-identity-federation).

## How it works

```
Workload → AppRole auth → Vault (OIDC issuer) → signed JWT
         → POST /v1/oauth/token → Anthropic (verifies JWT via JWKS)
         → short-lived access token → Claude API
```

1. A workload authenticates to Vault using AppRole (or any supported auth method).
2. Vault mints a signed JWT with the workload's identity claims and `aud: https://api.anthropic.com`.
3. The Anthropic SDK exchanges the JWT for a short-lived access token via the `/v1/oauth/token` endpoint.
4. The SDK calls the Claude API with the access token and refreshes it automatically before expiry.

No static Anthropic API key is created, distributed, or stored.

## What Terraform creates

| Resource | Count | Description |
| :--- | :---: | :--- |
| OIDC signing key | 1 | RS256, 24h rotation, scoped to `https://api.anthropic.com` |
| OIDC roles | 3 | One per environment (`research`, `build`, `prod`) |
| AppRole auth backend | 1 | With 3 roles for demo workloads |
| Identity entities | 3 | Each carrying `environment` and `team` metadata |
| Identity groups | 3 | `research-team`, `ci-runners`, `ai-platform` |
| Vault policies | 3 | Scoped to each environment's OIDC and AppRole paths |

### Environments

| Environment | OIDC role | Identity group | Intended consumer |
| :--- | :--- | :--- | :--- |
| Research | `anthropic-research-role` | `research-team` | Interactive exploration |
| Build | `anthropic-build-role` | `ci-runners` | CI/CD pipelines |
| Production | `anthropic-prod-role` | `ai-platform` | Runtime services |

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.10
- [Vault CLI](https://developer.hashicorp.com/vault/install) ≥ 1.12
- A Vault cluster (HCP Vault or self-managed) with the identity engine enabled
- An [Anthropic organization](https://console.anthropic.com) with API credits and Workload Identity Federation enabled
- Python 3.9+ and `jq`

## Quick start

### 1. Configure Terraform variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit with your Vault address and token
```

### 2. Apply Terraform

```bash
make init
make plan   # review the changes
make apply
```

### 3. Configure the Anthropic Console

Run the interactive wizard — it reads Terraform outputs, provides copy-paste values for each Console step, and writes a `.env` file:

```bash
make setup-anthropic
```

For manual instructions, see [ANTHROPIC_SETUP.md](ANTHROPIC_SETUP.md).

### 4. Run the federation test

```bash
source .env

# Generate an AppRole secret ID
make secret-id ENV=research
export VAULT_APPROLE_SECRET_ID=<secret_id from above>

# Set the Anthropic IDs (the wizard writes per-environment variables)
export ANTHROPIC_FEDERATION_RULE_ID=$ANTHROPIC_RESEARCH_FEDERATION_RULE_ID
export ANTHROPIC_SERVICE_ACCOUNT_ID=$ANTHROPIC_RESEARCH_SERVICE_ACCOUNT_ID

# Run the end-to-end test
make test ENV=research
```

The test script authenticates to Vault via AppRole, mints an OIDC token, exchanges it with Anthropic, and makes a Claude API call — all without a static API key.

## Repository structure

```
├── auth.tf                  # AppRole auth backend, roles, and secret ID access
├── identity.tf              # Entities, groups, and group memberships
├── oidc.tf                  # OIDC key, roles, issuer config, and allowed client IDs
├── policies.tf              # Per-environment Vault policies
├── providers.tf             # Terraform provider configuration
├── variables.tf             # Input variables
├── outputs.tf               # OIDC URLs, role IDs, and Console setup instructions
├── terraform.tfvars.example # Example variable values
├── Makefile                 # Workflow targets (init, apply, test, etc.)
├── ANTHROPIC_SETUP.md       # Manual Anthropic Console setup instructions
└── scripts/
    ├── requirements.txt     # Python dependencies (anthropic, hvac)
    ├── setup_anthropic.py   # Interactive Console setup wizard
    └── test_federation.py   # End-to-end federation test
```

## Make targets

```
make help             Show all targets and workflow
make init             Terraform init
make plan             Terraform plan
make apply            Terraform apply
make setup-anthropic  Interactive Anthropic Console wizard
make check-oidc       Verify OIDC discovery and JWKS endpoints
make secret-id        Generate an AppRole secret ID (ENV=research|build|prod)
make test             Run the federation test (ENV=research|build|prod)
make outputs          Show all Terraform outputs
make clean            Remove virtualenv and Terraform working files
```

## Network considerations

Anthropic must reach Vault's JWKS endpoint to verify token signatures. Three options are covered in the blog post:

| Mode | How it works |
| :--- | :--- |
| **Edge proxy** | Expose only the OIDC discovery/JWKS paths through an ingress proxy. Simplest option. |
| **Zero trust tunnel** | Outbound-only tunnel publishes the JWKS endpoint. No inbound firewall changes. |
| **Inline JWKS** | Push Vault's public keys to Anthropic. Vault stays fully private; requires a key-sync job. |

If your Vault cluster serves on a non-443 port (e.g. HCP Vault on `:8200`), the setup wizard auto-detects this and guides you through inline JWKS mode.

## Cleanup

When you finish the demo, remove the issuer, service accounts, and federation rules from the Anthropic Claude Console.

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0) — see [LICENSE](LICENSE) for details.
