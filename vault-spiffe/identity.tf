# -----------------------------------------------------------------------------
# Identity entities — one per environment, with metadata for JWT-SVID claims
# -----------------------------------------------------------------------------
resource "vault_identity_entity" "demo" {
  for_each = var.environments

  name = "${each.key}-workload"

  metadata = {
    environment = each.value.environment
    team        = each.value.team
  }
}

# -----------------------------------------------------------------------------
# Entity aliases — bind each entity to its AppRole role
# -----------------------------------------------------------------------------
resource "vault_identity_entity_alias" "demo" {
  for_each = var.environments

  name           = vault_approle_auth_backend_role.demo[each.key].role_id
  mount_accessor = vault_auth_backend.approle.accessor
  canonical_id   = vault_identity_entity.demo[each.key].id
}
