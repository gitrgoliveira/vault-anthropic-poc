# -----------------------------------------------------------------------------
# OIDC discovery URLs — needed for Anthropic issuer registration
# -----------------------------------------------------------------------------
output "oidc_issuer_url" {
  value       = "${var.vault_address}/v1/${var.vault_namespace}/identity/oidc"
  description = "Register this as the Issuer URL in the Anthropic Claude Console."
}

output "oidc_discovery_url" {
  value       = "${var.vault_address}/v1/${var.vault_namespace}/identity/oidc/.well-known/openid-configuration"
  description = "OIDC discovery document URL. Anthropic fetches this in discovery JWKS mode."
}

output "oidc_jwks_url" {
  value       = "${var.vault_address}/v1/${var.vault_namespace}/identity/oidc/.well-known/keys"
  description = "JWKS URL containing the public signing keys."
}

# -----------------------------------------------------------------------------
# Vault address — base URL without path, for CLI commands
# -----------------------------------------------------------------------------
output "vault_address" {
  value       = var.vault_address
  description = "Vault cluster base URL (scheme + host + port)."
}

# -----------------------------------------------------------------------------
# AppRole credentials — needed to authenticate demo workloads
# -----------------------------------------------------------------------------
output "approle_role_ids" {
  value = {
    for k, v in vault_approle_auth_backend_role.demo : k => v.role_id
  }
  description = "AppRole role IDs for each environment. Pass these to the test script."
}

# -----------------------------------------------------------------------------
# OIDC role names — for constructing token read paths
# -----------------------------------------------------------------------------
output "oidc_role_names" {
  value = {
    for k, v in vault_identity_oidc_role.anthropic : k => v.name
  }
  description = "OIDC role names for each environment."
}

# -----------------------------------------------------------------------------
# Setup wizard inputs — values the interactive wizard needs from Terraform
# -----------------------------------------------------------------------------
output "anthropic_audience" {
  value       = var.anthropic_audience
  description = "Audience claim value for federation rules."
}

output "environment_configs" {
  value       = var.environments
  description = "Environment configurations for the setup wizard."
}

# -----------------------------------------------------------------------------
# Summary for Anthropic Console setup
# -----------------------------------------------------------------------------
output "anthropic_console_instructions" {
  value       = <<-EOT

    ============================================================
    ANTHROPIC CONSOLE SETUP
    ============================================================

    1. Go to Settings → Workload identity → Issuers tab
       - Name:       hcp-vault
       - Issuer URL: ${var.vault_address}/v1/${var.vault_namespace}/identity/oidc
       - JWKS mode:  inline (port 8200 requires inline; fetch keys with make check-jwks)

    2. Go to Settings → Service accounts
       Create one service account per environment:
       - research-worker
       - build-worker
       - prod-worker
       Add each to its corresponding workspace.

    3. Go to Settings → Workload identity → Federation rules tab
       Create one rule per environment:

       research-rule:
         Issuer:    hcp-vault
         Audience:  ${var.anthropic_audience}
         Condition: claims.metadata.environment == "research" && "research-team" in claims.groups
         Target:    research-worker service account
         Scope:     workspace:developer

       build-rule:
         Issuer:    hcp-vault
         Audience:  ${var.anthropic_audience}
         Condition: claims.metadata.environment == "build" && "ci-runners" in claims.groups
         Target:    build-worker service account
         Scope:     workspace:developer

       prod-rule:
         Issuer:    hcp-vault
         Audience:  ${var.anthropic_audience}
         Condition: claims.metadata.environment == "production" && "ai-platform" in claims.groups
         Target:    prod-worker service account
         Scope:     workspace:developer

    4. Note the IDs for the test script:
       - Federation rule IDs (fdrl_...)
       - Service account IDs (svac_...)
       - Organization ID (UUID from Settings → Organization)

    ============================================================
  EOT
  description = "Step-by-step instructions for configuring the Anthropic Console."
}
