# -----------------------------------------------------------------------------
# Policies — grant each workload read access to its OIDC token endpoint
# -----------------------------------------------------------------------------
resource "vault_policy" "oidc_token" {
  for_each = var.environments

  name = "anthropic-${each.key}-oidc"

  policy = <<-EOT
    # Allow the workload to read its own OIDC token
    path "identity/oidc/token/anthropic-${each.key}-role" {
      capabilities = ["read"]
    }
  EOT
}
