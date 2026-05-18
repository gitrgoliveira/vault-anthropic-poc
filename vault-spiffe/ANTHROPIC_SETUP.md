# Anthropic Console Setup

> **Automated option:** Run `make setup-anthropic` for an interactive wizard that
> walks you through every step below, provides copy-paste values from Terraform
> outputs, validates the IDs you enter, and writes a `.env` file.

After `terraform apply` completes, configure the Anthropic side in the
[Claude Console](https://console.anthropic.com).

The Terraform outputs print the values you need. Run:

```bash
terraform output
```

## 1. Register a federation issuer

Go to **Settings → Workload identity → Issuers** tab → **Create issuer**.

| Field | Value |
| :---- | :---- |
| Name | `hcp-vault-spiffe` |
| Issuer URL | `<spiffe_issuer_url from Terraform output>` |
| JWKS source | `inline` |
| Inline keys | `<see below>` |

> **Why inline?** Anthropic requires issuer URLs on port 443 for `discovery`
> mode, but HCP Vault often serves on port 8200. In `inline` mode the Issuer URL is
> only used for string comparison against the JWT `iss` claim and is never
> fetched, so non-443 ports work. You must update the inline keys whenever
> Vault rotates its signing key (default: every 24 hours, controlled by `key_lifetime` in `spiffe.tf`).

Fetch the current JWKS keys array from Vault:

```bash
curl -s "$(terraform output -raw spiffe_jwks_url)" | jq .keys
```

Paste the resulting JSON array into the **Inline keys** field.

## 2. Create service accounts

Go to **Settings → Service accounts → Create service account**.

Create one per environment:

| Name | Description |
| :---- | :---- |
| `spiffe-research-worker` | Research environment workloads |
| `spiffe-build-worker` | CI/CD pipeline workloads |
| `spiffe-prod-worker` | Production runtime workloads |

Add each service account to its corresponding workspace from that workspace's
**Members** page. Note the service account IDs (`svac_...`).

## 3. Create federation rules

Go to **Settings → Workload identity → Federation rules** tab → **Create rule**.

### spiffe-research-rule

| Field | Value |
| :---- | :---- |
| Name | `spiffe-research-rule` |
| Issuer | `hcp-vault-spiffe` |
| Subject prefix | `<spiffe_subjects.research from Terraform output>` |
| Audience | `https://api.anthropic.com` |
| Target | `spiffe-research-worker` service account |
| OAuth scope | `workspace:developer` |
| Token lifetime | `3600` |

### spiffe-build-rule

| Field | Value |
| :---- | :---- |
| Name | `spiffe-build-rule` |
| Issuer | `hcp-vault-spiffe` |
| Subject prefix | `<spiffe_subjects.build from Terraform output>` |
| Audience | `https://api.anthropic.com` |
| Target | `spiffe-build-worker` service account |
| OAuth scope | `workspace:developer` |
| Token lifetime | `3600` |

### spiffe-prod-rule

| Field | Value |
| :---- | :---- |
| Name | `spiffe-prod-rule` |
| Issuer | `hcp-vault-spiffe` |
| Subject prefix | `<spiffe_subjects.prod from Terraform output>` |
| Audience | `https://api.anthropic.com` |
| Target | `spiffe-prod-worker` service account |
| OAuth scope | `workspace:developer` |
| Token lifetime | `3600` |

Note each rule's ID (`fdrl_...`).

## 4. Collect IDs for the test script

You need three IDs per environment:

| Variable | Where to find it |
| :---- | :---- |
| `ANTHROPIC_ORGANIZATION_ID` | Settings → Organization (UUID) |
| `ANTHROPIC_FEDERATION_RULE_ID` | The `fdrl_...` ID from the rule you created |
| `ANTHROPIC_SERVICE_ACCOUNT_ID` | The `svac_...` ID from the service account |

Refer to the [README](README.md) for how to run the test script with these values.
