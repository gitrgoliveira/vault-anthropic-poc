.PHONY: help init plan apply destroy \
       check-oidc check-jwks check-discovery \
       secret-id test venv clean \
       fmt validate

# ─── Defaults ────────────────────────────────────────────────────────────────
ENV          ?= research
VENV_DIR     := scripts/.venv
PYTHON       := $(VENV_DIR)/bin/python
PIP          := $(VENV_DIR)/bin/pip
VAULT_NS     ?= admin

# ─── Help ────────────────────────────────────────────────────────────────────
help: ## Show this help
	@echo ""
	@echo "Vault OIDC → Anthropic WIF POC"
	@echo "=============================="
	@echo ""
	@echo "Workflow:"
	@echo "  1. make init          – terraform init"
	@echo "  2. make plan          – terraform plan (review changes)"
	@echo "  3. make apply         – terraform apply (provision Vault resources)"
	@echo "  4. make setup-anthropic – interactive wizard for Anthropic Console setup"
	@echo "  5. make check-oidc    – verify OIDC discovery + JWKS are reachable"
	@echo "  6. make secret-id     – generate an AppRole secret ID (ENV=research|build|prod)"
	@echo "  7. make test          – run the federation test script (ENV=research|build|prod)"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables:"
	@echo "  ENV                  Environment to target (research, build, prod). Default: research"
	@echo "  VAULT_NS             Vault namespace. Default: admin"
	@echo "  VAULT_ADDR           Vault URL fallback for plan/apply/destroy"
	@echo "  VAULT_TOKEN          Vault token fallback for plan/apply/destroy"
	@echo "  VAULT_SKIP_VERIFY    TLS verify toggle fallback (true/false) for plan/apply/destroy"
	@echo ""

# ─── Terraform ───────────────────────────────────────────────────────────────
init: ## Initialize Terraform and download providers
	terraform init -upgrade

fmt: ## Format Terraform files
	terraform fmt

validate: ## Validate Terraform configuration
	terraform validate

plan: ## Show Terraform execution plan
	@TF_VAR_vault_address=$${TF_VAR_vault_address:-$${VAULT_ADDR:-$$(grep -E '^\s*vault_address\s*=' terraform.tfvars 2>/dev/null | sed 's/.*= *"\(.*\)"/\1/' | head -1)}} && \
	TF_VAR_vault_token=$${TF_VAR_vault_token:-$${VAULT_TOKEN:-$$(grep -E '^\s*vault_token\s*=' terraform.tfvars 2>/dev/null | sed 's/.*= *"\(.*\)"/\1/' | head -1)}} && \
	TF_VAR_vault_skip_verify=$${TF_VAR_vault_skip_verify:-$${VAULT_SKIP_VERIFY:-$$(grep -E '^\s*vault_skip_verify\s*=' terraform.tfvars 2>/dev/null | sed 's/.*= *\(.*\)/\1/' | tr -d ' ' | head -1)}} && \
	if [ -z "$$TF_VAR_vault_address" ]; then echo "ERROR: Set VAULT_ADDR or TF_VAR_vault_address (or add vault_address to terraform.tfvars)."; exit 1; fi && \
	if [ -z "$$TF_VAR_vault_token" ]; then echo "ERROR: Set VAULT_TOKEN or TF_VAR_vault_token (or add vault_token to terraform.tfvars)."; exit 1; fi && \
	TF_VAR_vault_address="$$TF_VAR_vault_address" TF_VAR_vault_token="$$TF_VAR_vault_token" TF_VAR_vault_skip_verify="$${TF_VAR_vault_skip_verify:-false}" terraform plan

apply: ## Apply Terraform configuration to Vault
	@TF_VAR_vault_address=$${TF_VAR_vault_address:-$${VAULT_ADDR:-$$(grep -E '^\s*vault_address\s*=' terraform.tfvars 2>/dev/null | sed 's/.*= *"\(.*\)"/\1/' | head -1)}} && \
	TF_VAR_vault_token=$${TF_VAR_vault_token:-$${VAULT_TOKEN:-$$(grep -E '^\s*vault_token\s*=' terraform.tfvars 2>/dev/null | sed 's/.*= *"\(.*\)"/\1/' | head -1)}} && \
	TF_VAR_vault_skip_verify=$${TF_VAR_vault_skip_verify:-$${VAULT_SKIP_VERIFY:-$$(grep -E '^\s*vault_skip_verify\s*=' terraform.tfvars 2>/dev/null | sed 's/.*= *\(.*\)/\1/' | tr -d ' ' | head -1)}} && \
	if [ -z "$$TF_VAR_vault_address" ]; then echo "ERROR: Set VAULT_ADDR or TF_VAR_vault_address (or add vault_address to terraform.tfvars)."; exit 1; fi && \
	if [ -z "$$TF_VAR_vault_token" ]; then echo "ERROR: Set VAULT_TOKEN or TF_VAR_vault_token (or add vault_token to terraform.tfvars)."; exit 1; fi && \
	TF_VAR_vault_address="$$TF_VAR_vault_address" TF_VAR_vault_token="$$TF_VAR_vault_token" TF_VAR_vault_skip_verify="$${TF_VAR_vault_skip_verify:-false}" terraform apply

destroy: ## Destroy all Terraform-managed resources
	@TF_VAR_vault_address=$${TF_VAR_vault_address:-$${VAULT_ADDR:-$$(grep -E '^\s*vault_address\s*=' terraform.tfvars 2>/dev/null | sed 's/.*= *"\(.*\)"/\1/' | head -1)}} && \
	TF_VAR_vault_token=$${TF_VAR_vault_token:-$${VAULT_TOKEN:-$$(grep -E '^\s*vault_token\s*=' terraform.tfvars 2>/dev/null | sed 's/.*= *"\(.*\)"/\1/' | head -1)}} && \
	TF_VAR_vault_skip_verify=$${TF_VAR_vault_skip_verify:-$${VAULT_SKIP_VERIFY:-$$(grep -E '^\s*vault_skip_verify\s*=' terraform.tfvars 2>/dev/null | sed 's/.*= *\(.*\)/\1/' | tr -d ' ' | head -1)}} && \
	if [ -z "$$TF_VAR_vault_address" ]; then echo "ERROR: Set VAULT_ADDR or TF_VAR_vault_address (or add vault_address to terraform.tfvars)."; exit 1; fi && \
	if [ -z "$$TF_VAR_vault_token" ]; then echo "ERROR: Set VAULT_TOKEN or TF_VAR_vault_token (or add vault_token to terraform.tfvars)."; exit 1; fi && \
	TF_VAR_vault_address="$$TF_VAR_vault_address" TF_VAR_vault_token="$$TF_VAR_vault_token" TF_VAR_vault_skip_verify="$${TF_VAR_vault_skip_verify:-false}" terraform destroy

# ─── OIDC verification ──────────────────────────────────────────────────────
check-oidc: check-discovery check-jwks ## Verify both OIDC discovery and JWKS endpoints

check-discovery: ## Fetch the OIDC discovery document
	@echo "── OIDC Discovery ─────────────────────────────────"
	@ISSUER=$$(terraform output -raw oidc_discovery_url) && \
		echo "GET $$ISSUER" && echo "" && \
		curl -sf "$$ISSUER" | jq .

check-jwks: ## Fetch the JWKS (public signing keys)
	@echo "── JWKS ───────────────────────────────────────────"
	@JWKS=$$(terraform output -raw oidc_jwks_url) && \
		echo "GET $$JWKS" && echo "" && \
		curl -sf "$$JWKS" | jq .

# ─── AppRole secret ID ──────────────────────────────────────────────────────
secret-id: ## Generate an AppRole secret ID (set ENV=research|build|prod)
	@echo "── Generating secret ID for $(ENV)-workload ─────"
	@VAULT_ADDR=$$(terraform output -raw vault_address) && \
	VAULT_TOKEN=$${VAULT_TOKEN:-$$(grep -E '^\s*vault_token' terraform.tfvars | sed 's/.*= *"\(.*\)"/\1/' | head -1)} && \
	if [ -z "$$VAULT_TOKEN" ]; then echo "ERROR: Set VAULT_TOKEN or add vault_token to terraform.tfvars"; exit 1; fi && \
	VAULT_ADDR="$$VAULT_ADDR" VAULT_NAMESPACE="$(VAULT_NS)" VAULT_TOKEN="$$VAULT_TOKEN" \
	vault write -f "auth/approle/role/$(ENV)-workload/secret-id"

# ─── Python virtualenv ──────────────────────────────────────────────────────
venv: $(VENV_DIR)/bin/activate ## Create Python virtualenv and install dependencies

$(VENV_DIR)/bin/activate: scripts/requirements.txt
	python3 -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install -r scripts/requirements.txt
	touch $(VENV_DIR)/bin/activate

# ─── Test federation ────────────────────────────────────────────────────────
test: venv ## Run the federation test (set ENV and Anthropic env vars)
	@echo "── Federation test ($(ENV)) ────────────────────────"
	@ROLE_ID=$$(terraform output -json approle_role_ids | jq -r '.$(ENV)') && \
	OIDC_ROLE=$$(terraform output -json oidc_role_names | jq -r '.$(ENV)') && \
	VAULT_ADDR=$$(terraform output -raw vault_address) && \
	echo "VAULT_ADDR=$$VAULT_ADDR" && \
	echo "VAULT_APPROLE_ROLE_ID=$$ROLE_ID" && \
	echo "VAULT_OIDC_ROLE=$$OIDC_ROLE" && \
	echo "" && \
	VAULT_ADDR="$$VAULT_ADDR" \
	VAULT_NAMESPACE="$(VAULT_NS)" \
	VAULT_APPROLE_ROLE_ID="$$ROLE_ID" \
	VAULT_APPROLE_SECRET_ID="$${VAULT_APPROLE_SECRET_ID:?Set VAULT_APPROLE_SECRET_ID (run: make secret-id ENV=$(ENV))}" \
	VAULT_OIDC_ROLE="$$OIDC_ROLE" \
	ANTHROPIC_ORGANIZATION_ID="$${ANTHROPIC_ORGANIZATION_ID:?Set ANTHROPIC_ORGANIZATION_ID}" \
	ANTHROPIC_FEDERATION_RULE_ID="$${ANTHROPIC_FEDERATION_RULE_ID:?Set ANTHROPIC_FEDERATION_RULE_ID}" \
	ANTHROPIC_SERVICE_ACCOUNT_ID="$${ANTHROPIC_SERVICE_ACCOUNT_ID:?Set ANTHROPIC_SERVICE_ACCOUNT_ID}" \
	ANTHROPIC_WORKSPACE_ID="$${ANTHROPIC_WORKSPACE_ID:-}" \
	$(PYTHON) scripts/test_federation.py

# ─── Anthropic Console setup ─────────────────────────────────────────────────
setup-anthropic: venv ## Interactive wizard to configure the Anthropic Console
	$(PYTHON) scripts/setup_anthropic.py

# ─── Outputs ─────────────────────────────────────────────────────────────────
outputs: ## Show all Terraform outputs
	terraform output

console-instructions: ## Print Anthropic Console setup instructions
	@terraform output -raw anthropic_console_instructions

# ─── Cleanup ─────────────────────────────────────────────────────────────────
clean: ## Remove virtualenv and Terraform working files
	rm -rf $(VENV_DIR)
	rm -rf .terraform
	rm -f .terraform.lock.hcl
