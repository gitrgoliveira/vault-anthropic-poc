# Vault OIDC → Anthropic Workload Identity Federation

> Use HashiCorp Vault's identity OIDC engine to mint signed JWTs that Anthropic exchanges for short-lived access tokens.

Replace static `sk-ant-...` API keys with ephemeral, identity-bound tokens by configuring HashiCorp Vault as an OIDC issuer for [Anthropic Workload Identity Federation](https://platform.claude.com/docs/en/manage-claude/workload-identity-federation).

## How it works

```text
Workload → AppRole auth → Vault (OIDC issuer) → signed JWT
         → POST /v1/oauth/token → Anthropic (verifies JWT via JWKS)
         → short-lived access token → Claude API
```

1. A workload authenticates to Vault using AppRole (or any supported auth method).
2. Vault mints a signed JWT with the workload's identity claims and `aud: https://api.anthropic.com`.
3. The Anthropic SDK exchanges the JWT for a short-lived access token via the `/v1/oauth/token` endpoint.
4. The SDK calls the Claude API with the access token and refreshes it automatically before expiry.

You do not create, distribute, or store a static Anthropic API key.

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

Run all commands from this directory:

```bash
cd vault-oidc
```

### 1. Configure Terraform variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit with your Vault address and token
```

### 2. Apply Terraform

```bash
make init
make plan
make apply
```

### 3. Configure the Anthropic Console

Run the interactive wizard. It reads Terraform outputs, provides copy-paste values for each console step, and writes a `.env` file in `vault-oidc/`:

```bash
make setup-anthropic
```

For manual instructions, refer to [ANTHROPIC_SETUP.md](ANTHROPIC_SETUP.md).

### 4. Run the federation test

```bash
source .env

# Generate an AppRole secret ID
make secret-id ENV=research
export VAULT_APPROLE_SECRET_ID=<secret_id from make secret-id>

# Set the Anthropic IDs (the wizard writes per-environment variables)
export ANTHROPIC_FEDERATION_RULE_ID=$ANTHROPIC_RESEARCH_FEDERATION_RULE_ID
export ANTHROPIC_SERVICE_ACCOUNT_ID=$ANTHROPIC_RESEARCH_SERVICE_ACCOUNT_ID

# Run the end-to-end test
make test ENV=research
```

The test script authenticates to Vault via AppRole, mints an OIDC token, exchanges it with Anthropic, and makes a Claude API call, all without a static API key.

## Directory structure

```text
vault-oidc/
├── auth.tf
├── identity.tf
├── oidc.tf
├── outputs.tf
├── policies.tf
├── providers.tf
├── variables.tf
├── terraform.tfvars.example
├── Makefile
├── ANTHROPIC_SETUP.md
└── scripts/
    ├── requirements.txt
    ├── setup_anthropic.py
    └── test_federation.py
```

## Make targets

```text
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

Anthropic must reach Vault's JWKS endpoint to verify token signatures. Three options are common:

| Mode | How it works |
| :--- | :--- |
| **Edge proxy** | Expose only the OIDC discovery and JWKS paths through an ingress proxy. |
| **Zero trust tunnel** | An outbound-only tunnel publishes the JWKS endpoint. |
| **Inline JWKS** | Push Vault's public keys to Anthropic. Vault stays private, but you must sync keys after rotation. |

If your Vault cluster serves on a non-443 port, for example HCP Vault on `:8200`, the setup wizard detects this and guides you through inline JWKS mode.

## Troubleshooting

| Symptom | Likely cause | Fix |
| :--- | :--- | :--- |
| CEL condition evaluates to `false` despite correct entity metadata | Entity is not a member of the expected identity group. The JWT `groups` claim is `[]` when no group membership exists. | Verify the entity alias linked correctly: `vault read identity/entity/id/<id>` and check `group_ids`. Re-apply Terraform if the alias is missing. |
| Token exchange returns 401 | The `iss` claim in the JWT does not match the Issuer URL registered in Anthropic. | Run `make check-oidc` and confirm the discovery document `issuer` matches `oidc_issuer_url` from Terraform output. |
| `ANTHROPIC_API_KEY` shadows federation | The SDK prefers `ANTHROPIC_API_KEY` over WIF. | Unset `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` before running the test. |

## Cleanup

When you finish the demo, remove the issuer, service accounts, and federation rules from the Claude Console.

## See also

[Vault SPIFFE → Anthropic WIF](../vault-spiffe/README.md) uses Vault's SPIFFE secrets engine (Enterprise) for SPIFFE URI-based workload identities instead of OIDC claims.

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0). See [../LICENSE](../LICENSE).
