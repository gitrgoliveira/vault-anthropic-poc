variable "vault_address" {
  type        = string
  description = "Vault cluster URL (for example, https://vault.example.com:8200). Set with TF_VAR_vault_address or use VAULT_ADDR via the Makefile wrappers."

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
  default     = ""
  description = "Leave empty for OSS/dev mode or set to 'admin' for HCP Vault."
}

variable "vault_token" {
  type        = string
  ephemeral   = true
  description = "Vault token with permissions to manage identity, auth, and policy resources. Never persisted to state or plan files. Set with TF_VAR_vault_token or use VAULT_TOKEN via the Makefile wrappers."
}

variable "vault_skip_verify" {
  type        = bool
  default     = false
  description = "Skip TLS certificate verification for Vault API calls (useful for local dev TLS). Set with TF_VAR_vault_skip_verify or VAULT_SKIP_VERIFY via the Makefile wrappers."
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
