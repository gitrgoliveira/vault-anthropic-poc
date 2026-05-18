# -----------------------------------------------------------------------------
# AppRole auth backend (demo workload authentication)
# -----------------------------------------------------------------------------
resource "vault_auth_backend" "approle" {
  type = "approle"
  path = "spiffe-approle"
}

# -----------------------------------------------------------------------------
# AppRole roles — one per environment
# -----------------------------------------------------------------------------
resource "vault_approle_auth_backend_role" "demo" {
  for_each = var.environments

  backend            = vault_auth_backend.approle.path
  role_name          = "${each.key}-workload"
  token_policies     = [vault_policy.spiffe_token[each.key].name]
  token_ttl          = 3600
  token_max_ttl      = 7200
  secret_id_ttl      = 3600
  secret_id_num_uses = 1
}
