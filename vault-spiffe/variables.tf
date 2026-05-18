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
  description = "Vault token with permissions to manage SPIFFE, auth, identity, and policy resources. Never persisted to state or plan files."
}

variable "trust_domain" {
  type        = string
  description = "SPIFFE trust domain for minted JWT-SVIDs, without the spiffe:// prefix (for example, ai.internal)."

  validation {
    condition     = !startswith(var.trust_domain, "spiffe://")
    error_message = "trust_domain must not include the spiffe:// prefix."
  }
}

variable "anthropic_audience" {
  type        = string
  default     = "https://api.anthropic.com"
  description = "The audience claim (aud) that Anthropic federation rules expect."
}

variable "environments" {
  type = map(object({
    environment    = string
    team           = string
    spiffe_id_path = string
  }))
  default = {
    research = {
      environment    = "research"
      team           = "research-team"
      spiffe_id_path = "/workload/research"
    }
    build = {
      environment    = "build"
      team           = "ci-runners"
      spiffe_id_path = "/workload/build"
    }
    prod = {
      environment    = "production"
      team           = "ai-platform"
      spiffe_id_path = "/workload/prod"
    }
  }
  description = "Map of environment configurations. Each entry creates a SPIFFE role, AppRole role, entity, and policy."
}
