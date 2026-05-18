# -----------------------------------------------------------------------------
# Identity entities — one per environment, with metadata for JWT-SVID claims
# -----------------------------------------------------------------------------

resource "vault_identity_entity" "spiffe" {
  for_each = var.environments

  name = "spiffe-${each.key}-workload"

  metadata = {
    environment = each.value.environment
    team        = each.value.team
    purpose     = "Anthropic SPIFFE federation"
  }
}

# -----------------------------------------------------------------------------
# Entity aliases — bind each entity to its AppRole role
# -----------------------------------------------------------------------------

resource "vault_identity_entity_alias" "spiffe" {
  for_each = var.environments

  name           = vault_approle_auth_backend_role.demo[each.key].role_id
  mount_accessor = vault_auth_backend.approle.accessor
  canonical_id   = vault_identity_entity.spiffe[each.key].id
}
