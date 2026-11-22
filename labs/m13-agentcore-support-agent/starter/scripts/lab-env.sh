#!/usr/bin/env bash
# Print the lab identifiers as export lines (bash or zsh):
#   eval "$(./scripts/lab-env.sh)"
# Before the support-agent stack exists, only the API values are printed.
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require terraform

echo "export AWS_REGION=$AWS_REGION"
echo "export API_ID=$(api_output api_id)"
echo "export API_URL=$(api_output api_url)"
echo "export TF_VAR_acme_api_url=$(api_output api_url)"
if runtime_arn="$(agent_output runtime_arn 2>/dev/null)"; then
  echo "export RUNTIME_ARN=$runtime_arn"
  echo "export RUNTIME_ID=$(agent_output runtime_id)"
  echo "export GATEWAY_ARN=$(agent_output gateway_arn)"
  echo "export MEMORY_ID=$(agent_output memory_id)"
fi
