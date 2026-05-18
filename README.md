# Vault → Anthropic - Workload Identity Federation Guides

This repository contains two self-contained guides for replacing static Anthropic API keys with short-lived federated credentials issued by Vault.

## Choose a guide

| Guide | Use when | Path |
| :--- | :--- | :--- |
| Vault OIDC | You want to use Vault's identity engine as an OIDC issuer. | [`vault-oidc/`](vault-oidc/README.md) |
| Vault SPIFFE | You are already using SPIFFE identities and want Vault to mint SPIFFE JWT-SVIDs for Anthropic. Requires the Vault Enterprise SPIFFE secrets engine. | [`vault-spiffe/`](vault-spiffe/README.md) |

## Comparison

| Aspect | Vault OIDC | Vault SPIFFE |
| :--- | :--- | :--- |
| Vault feature | Identity engine | SPIFFE secrets engine |
| Anthropic matcher style | CEL over claims and groups | `subject_prefix` plus `audience` |
| Token type | OIDC JWT | SPIFFE JWT-SVID |
| Vault edition | Community or Enterprise | Enterprise |
| Best fit | Existing Vault identity workflows | SPIFFE-oriented workload identity |

## Repository layout

```text
.
├── LICENSE
├── README.md
├── vault-oidc/
│   ├── README.md
│   ├── ANTHROPIC_SETUP.md
│   ├── Makefile
│   ├── *.tf
│   └── scripts/
└── vault-spiffe/
    ├── README.md
    ├── ANTHROPIC_SETUP.md
    ├── Makefile
    ├── *.tf
    └── scripts/
```

## A note on AppRole

Both guides use [AppRole](https://developer.hashicorp.com/vault/docs/auth/approle) for workload authentication because it is simple to demonstrate end-to-end in a POC. In production you would typically replace it with:

- [**Vault Agent**](https://developer.hashicorp.com/vault/docs/agent-and-proxy/agent) for VM or bare-metal workloads, which handles login, token renewal, and secret templating automatically.
- [**Vault Secrets Operator**](https://developer.hashicorp.com/vault/docs/platform/k8s/vso) (VSO) for Kubernetes workloads, which syncs Vault secrets into native Kubernetes Secrets and manages lifecycle without application-side code.

The federation flow itself (mint a JWT, exchange it with Anthropic) is identical regardless of which auth method delivers the Vault token to your workload.

## Start here

Pick one directory and follow its guide from start to finish:

- [`vault-oidc/README.md`](vault-oidc/README.md)
- [`vault-spiffe/README.md`](vault-spiffe/README.md)

Each guide is independent. They keep their own Terraform, scripts, and local `.env` file.

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0). See [LICENSE](LICENSE).
