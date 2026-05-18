# Vault SPIFFE → Anthropic Workload Identity Federation

Use HashiCorp Vault's SPIFFE secrets engine to mint JWT-SVIDs that Anthropic exchanges for short-lived access tokens.

> **Important:** Anthropic Workload Identity Federation accepts SPIFFE JWT-SVIDs only. It does not accept X.509-SVIDs.

## How it works

```text
Workload → AppRole auth → Vault SPIFFE secrets engine → JWT-SVID
         → POST /v1/oauth/token → Anthropic (verifies JWT via JWKS)
         → short-lived access token → Claude API
```

1. A workload authenticates to Vault using AppRole.
2. Vault mints a SPIFFE JWT-SVID with `sub` set to the workload's SPIFFE ID and `aud: https://api.anthropic.com`.
3. The Anthropic SDK exchanges the JWT-SVID for a short-lived access token.
4. The SDK calls the Claude API with the exchanged token.

You do not create, distribute, or store a static Anthropic API key.

## What Terraform creates

| Resource | Count | Description |
| :--- | :---: | :--- |
| SPIFFE secrets engine | 1 | Mounted at `spiffe/` |
| SPIFFE roles | 3 | One per environment (`research`, `build`, `prod`) |
| AppRole auth backend | 1 | With 3 roles for demo workloads |
| Identity entities | 3 | Each carrying `environment` and `team` metadata |
| Vault policies | 3 | Scoped to each environment's SPIFFE mint path |

### Environments

| Environment | SPIFFE role | SPIFFE ID | Intended consumer |
| :--- | :--- | :--- | :--- |
| Research | `research-workload` | `spiffe://<trust-domain>/workload/research` | Interactive exploration |
| Build | `build-workload` | `spiffe://<trust-domain>/workload/build` | CI/CD pipelines |
| Production | `prod-workload` | `spiffe://<trust-domain>/workload/prod` | Runtime services |

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.10
- [Vault CLI](https://developer.hashicorp.com/vault/install) ≥ 1.12
- A Vault Enterprise cluster with the SPIFFE secrets engine available
- An [Anthropic organization](https://console.anthropic.com) with API credits and Workload Identity Federation enabled
- Python 3.9+ and `jq`

## Quick start

Run all commands from this directory:

```bash
cd vault-spiffe
```

### 1. Configure Terraform variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit with your Vault address, token, and SPIFFE trust domain
```

### 2. Apply Terraform

```bash
make init
make plan
make apply
```

> **Required: verify the issuer URL before proceeding.** Run `make check-spiffe`
> and confirm the `issuer` field in the discovery document **exactly matches** the
> `spiffe_issuer_url` Terraform output. If they differ, the `iss` claim in minted
> JWT-SVIDs will not match the value registered in Anthropic, and every token
> exchange will fail silently. Do not continue until the values match.

### 3. Configure the Anthropic Console

Run the interactive wizard. It reads Terraform outputs, provides copy-paste values for each console step, and writes a `.env` file in `vault-spiffe/`:

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

The test script authenticates to Vault via AppRole, mints a JWT-SVID, exchanges it with Anthropic, and makes a Claude API call, all without a static API key.

## Directory structure

```text
vault-spiffe/
├── auth.tf
├── identity.tf
├── outputs.tf
├── policies.tf
├── providers.tf
├── spiffe.tf
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
make check-spiffe     Verify SPIFFE discovery and JWKS endpoints
make secret-id        Generate an AppRole secret ID (ENV=research|build|prod)
make test             Run the federation test (ENV=research|build|prod)
make outputs          Show all Terraform outputs
make clean            Remove virtualenv and Terraform working files
```

## Network considerations

Anthropic must verify the JWT-SVID signing keys through the SPIFFE issuer's JWKS. If your Vault cluster serves on a non-443 port, for example HCP Vault on `:8200`, use inline JWKS mode in the Claude Console. The setup wizard detects this and prints the current key set.

## Operational notes

### No automatic drift detection

The SPIFFE secrets engine uses `vault_generic_endpoint` with `disable_read = true` because the endpoints do not support `GET`. As a result, `terraform plan` cannot detect manual changes made directly in Vault (for example, via CLI or API). The Terraform state reflects what was last written, not the live configuration. If you suspect drift, compare the live SPIFFE config with `vault read spiffe/config` and role definitions with `vault read spiffe/role/<name>` against [spiffe.tf](spiffe.tf).

## Cleanup

When you finish the demo, remove the issuer, service accounts, and federation rules from the Claude Console.

## See also

[Vault OIDC → Anthropic WIF](../vault-oidc/README.md) uses Vault's identity OIDC engine and is available on Community and Enterprise editions.

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0). See [../LICENSE](../LICENSE).
