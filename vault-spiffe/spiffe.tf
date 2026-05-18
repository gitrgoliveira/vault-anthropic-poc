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
resource "vault_generic_endpoint" "spiffe_config" {
  path = "${vault_mount.spiffe.path}/config"

  data_json = jsonencode({
    trust_domain                = var.trust_domain
    bundle_refresh_hint         = "1h"
    key_lifetime                = "24h"
    jwt_issuer_url              = "${var.vault_address}/v1/${var.vault_namespace}"
    jwt_oidc_compatibility_mode = true
    jwt_signing_algorithm       = "RS256"
  })

  disable_read         = true
  disable_delete       = true # The SPIFFE mount itself is destroyed by vault_mount.spiffe
  ignore_absent_fields = true
}

# -----------------------------------------------------------------------------
# SPIFFE roles — one per environment
# Anthropic WIF accepts JWT-SVIDs only, not X.509-SVIDs.
# -----------------------------------------------------------------------------
resource "vault_generic_endpoint" "spiffe_role" {
  for_each = var.environments

  path = "${vault_mount.spiffe.path}/role/${each.key}-workload"

  data_json = jsonencode({
    template = jsonencode({
      sub         = "spiffe://${var.trust_domain}${each.value.spiffe_id_path}"
      environment = each.value.environment
      team        = each.value.team
    })
    ttl           = "15m"
    use_jti_claim = true
  })

  disable_read         = true
  ignore_absent_fields = true

  depends_on = [vault_generic_endpoint.spiffe_config]
}
