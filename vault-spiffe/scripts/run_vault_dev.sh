#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

LOG_DIR="${LOG_DIR:-${ROOT_DIR}/logs}"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/vault-dev.log}"
ENV_FILE="${ENV_FILE:-${LOG_DIR}/vault-dev.env}"
VAULT_HOSTNAME="${VAULT_HOSTNAME:-localhost}"
VAULT_PORT="${VAULT_PORT:-8200}"
DEV_ROOT_TOKEN="${VAULT_DEV_ROOT_TOKEN:-root}"
VAULT_ADDR_VALUE="${VAULT_ADDR:-https://${VAULT_HOSTNAME}:${VAULT_PORT}}"

mkdir -p "${LOG_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Vault in dev mode"
echo "Logging output to: ${LOG_FILE}"
echo "Vault address: ${VAULT_ADDR_VALUE}"

vault server -dev -dev-tls -dev-root-token-id="${DEV_ROOT_TOKEN}" > "${LOG_FILE}" 2>&1 &
VAULT_PID=$!

cat > "${ENV_FILE}" <<EOF
export VAULT_ADDR="${VAULT_ADDR_VALUE}"
export VAULT_TOKEN="${DEV_ROOT_TOKEN}"
export VAULT_SKIP_VERIFY="true"
EOF

echo "Vault dev server started in background with TLS enabled"
echo "Vault PID: ${VAULT_PID}"
echo "Environment file written to: ${ENV_FILE}"
echo "Run this to load env vars in your shell: source \"${ENV_FILE}\""
