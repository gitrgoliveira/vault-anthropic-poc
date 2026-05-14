# -----------------------------------------------------------------------------
# OIDC provider config — pin the issuer to the public cluster URL
# Without this, Vault uses the internal node address in the iss claim.
# -----------------------------------------------------------------------------
resource "vault_identity_oidc" "config" {
  issuer = var.vault_address
}

# -----------------------------------------------------------------------------
# OIDC signing key
# -----------------------------------------------------------------------------
resource "vault_identity_oidc_key" "anthropic" {
  name               = "anthropic-key"
  algorithm          = "RS256"
  rotation_period    = 86400  # 24 hours
  verification_ttl   = 172800 # 48 hours — must exceed rotation_period + token TTL to survive key rotation + JWKS cache lag
  allowed_client_ids = [var.anthropic_audience]
}

# -----------------------------------------------------------------------------
# OIDC roles — one per environment (research, build, prod)
# -----------------------------------------------------------------------------
resource "vault_identity_oidc_role" "anthropic" {
  for_each = var.environments

  name      = "anthropic-${each.key}-role"
  key       = vault_identity_oidc_key.anthropic.name
  client_id = var.anthropic_audience
  ttl       = 900 # 15 minutes

  template = <<-EOT
    {
      "entity_name": {{identity.entity.name}},
      "groups": {{identity.entity.groups.names}},
      "metadata": {{identity.entity.metadata}}
    }
  EOT
}
