variable "vault_address" {
  type        = string
  description = "HCP Vault cluster public URL (e.g. https://vault-cluster.vault.xxxxxxxx.aws.hashicorp.cloud:8200)."

  validation {
    condition     = startswith(var.vault_address, "https://")
    error_message = "vault_address must use HTTPS (e.g. https://vault.example.com:8200)."
  }

  validation {
    condition     = !endswith(var.vault_address, "/")
    error_message = "vault_address must not include a trailing slash."
  }
}

variable "vault_namespace" {
  type        = string
  default     = "admin"
  description = "HCP Vault namespace. Defaults to the HCP root namespace."
}

variable "vault_token" {
  type        = string
  ephemeral   = true
  description = "Vault token with permissions to manage identity, auth, and policy resources. Never persisted to state or plan files."
}

variable "anthropic_audience" {
  type        = string
  default     = "https://api.anthropic.com"
  description = "The audience claim (aud) that Anthropic federation rules expect."
}

variable "environments" {
  type = map(object({
    environment = string
    team        = string
    group_name  = string
  }))
  default = {
    research = {
      environment = "research"
      team        = "research-team"
      group_name  = "research-team"
    }
    build = {
      environment = "build"
      team        = "ci-runners"
      group_name  = "ci-runners"
    }
    prod = {
      environment = "production"
      team        = "ai-platform"
      group_name  = "ai-platform"
    }
  }
  description = "Map of environment configurations. Each entry creates an OIDC role, AppRole role, entity, group, and policy."
}
