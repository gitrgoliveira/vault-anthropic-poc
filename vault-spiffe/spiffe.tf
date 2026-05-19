# -----------------------------------------------------------------------------
# SPIFFE secrets engine — Vault Enterprise required
# -----------------------------------------------------------------------------
resource "vault_mount" "spiffe" {
  path        = "spiffe"
  type        = "spiffe"
  description = "SPIFFE JWT-SVID issuer for Anthropic federation"
}

# -----------------------------------------------------------------------------
# SPIFFE engine configuration
# jwt_issuer_url uses the namespace-aware v1 base. Vault appends the mount path.
# -----------------------------------------------------------------------------

resource "vault_spiffe_secret_backend_config" "spiffe_config" {
  mount                       = vault_mount.spiffe.path
  trust_domain                = var.trust_domain
  bundle_refresh_hint         = "1h"
  key_lifetime                = "24h"
  jwt_issuer_url              = "${var.vault_address}/v1/${var.vault_namespace}"
  jwt_oidc_compatibility_mode = true
  jwt_signing_algorithm       = "RS256"
}

# -----------------------------------------------------------------------------
# SPIFFE roles — one per environment
# Anthropic WIF accepts JWT-SVIDs only, not X.509-SVIDs.
# -----------------------------------------------------------------------------

resource "vault_spiffe_secret_backend_role" "spiffe_role" {
  for_each = var.environments

  mount = vault_mount.spiffe.path
  name  = "${each.key}-workload"
  template = jsonencode({
    sub         = "spiffe://${var.trust_domain}${each.value.spiffe_id_path}"
    environment = each.value.environment
    team        = each.value.team
  })
  ttl           = "15m"
  use_jti_claim = true

  depends_on = [vault_spiffe_secret_backend_config.spiffe_config]
}
