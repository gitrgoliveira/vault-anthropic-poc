# -----------------------------------------------------------------------------
# SPIFFE OIDC discovery URLs — needed for Anthropic issuer registration
# -----------------------------------------------------------------------------
output "spiffe_issuer_url" {
  value       = "${var.vault_address}/v1/${var.vault_namespace}/${vault_mount.spiffe.path}"
  description = "Register this as the Issuer URL in the Anthropic Claude Console."
}

output "spiffe_discovery_url" {
  value       = "${var.vault_address}/v1/${var.vault_namespace}/${vault_mount.spiffe.path}/.well-known/openid-configuration"
  description = "OIDC discovery document URL for the SPIFFE JWT issuer."
}

output "spiffe_jwks_url" {
  value       = "${var.vault_address}/v1/${var.vault_namespace}/${vault_mount.spiffe.path}/.well-known/keys"
  description = "JWKS URL containing the SPIFFE JWT signing keys."
}

output "spiffe_trust_domain" {
  value       = var.trust_domain
  description = "SPIFFE trust domain used for minted JWT-SVIDs."
}

output "spiffe_role_names" {
  value = {
    for k, v in var.environments : k => "${k}-workload"
  }
  description = "SPIFFE role names for each environment."
}

output "spiffe_subjects" {
  value = {
    for k, v in var.environments : k => "spiffe://${var.trust_domain}${v.spiffe_id_path}"
  }
  description = "SPIFFE IDs minted for each environment."
}

output "vault_address" {
  value       = var.vault_address
  description = "Vault cluster base URL (scheme + host + port)."
}

output "approle_role_ids" {
  value = {
    for k, v in vault_approle_auth_backend_role.demo : k => v.role_id
  }
  description = "AppRole role IDs for each environment. Pass these to the test script."
}

output "anthropic_audience" {
  value       = var.anthropic_audience
  description = "Audience claim value for federation rules."
}

output "environment_configs" {
  value       = var.environments
  description = "Environment configurations for the setup wizard."
}

output "anthropic_console_instructions" {
  value       = <<-EOT

    ============================================================
    ANTHROPIC CONSOLE SETUP
    ============================================================

    1. Go to Settings → Workload identity → Issuers tab
       - Name:       hcp-vault-spiffe
       - Issuer URL: ${var.vault_address}/v1/${var.vault_namespace}/${vault_mount.spiffe.path}
       - JWKS mode:  inline (port 8200 requires inline; fetch keys with make check-jwks)

    2. Go to Settings → Service accounts
       Create one service account per environment:
       - spiffe-research-worker
       - spiffe-build-worker
       - spiffe-prod-worker
       Add each to its corresponding workspace.

    3. Go to Settings → Workload identity → Federation rules tab
       Create one rule per environment:

       spiffe-research-rule:
         Issuer:         hcp-vault-spiffe
         Subject prefix: spiffe://${var.trust_domain}/workload/research
         Audience:       ${var.anthropic_audience}
         Target:         spiffe-research-worker service account
         Scope:          workspace:developer

       spiffe-build-rule:
         Issuer:         hcp-vault-spiffe
         Subject prefix: spiffe://${var.trust_domain}/workload/build
         Audience:       ${var.anthropic_audience}
         Target:         spiffe-build-worker service account
         Scope:          workspace:developer

       spiffe-prod-rule:
         Issuer:         hcp-vault-spiffe
         Subject prefix: spiffe://${var.trust_domain}/workload/prod
         Audience:       ${var.anthropic_audience}
         Target:         spiffe-prod-worker service account
         Scope:          workspace:developer

    4. Note the IDs for the test script:
       - Federation rule IDs (fdrl_...)
       - Service account IDs (svac_...)
       - Organization ID (UUID from Settings → Organization)

    ============================================================
  EOT
  description = "Step-by-step instructions for configuring the Anthropic Console."
}
