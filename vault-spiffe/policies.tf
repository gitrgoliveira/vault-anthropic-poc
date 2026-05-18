# -----------------------------------------------------------------------------
# Policies — grant each workload permission to mint its own JWT-SVID
# -----------------------------------------------------------------------------
resource "vault_policy" "spiffe_token" {
  for_each = var.environments

  name = "anthropic-${each.key}-spiffe"

  policy = <<-EOT
    # Allow the workload to mint its own JWT-SVID
    path "${vault_mount.spiffe.path}/role/${each.key}-workload/mintjwt" {
      capabilities = ["create", "update"]
    }
  EOT
}
