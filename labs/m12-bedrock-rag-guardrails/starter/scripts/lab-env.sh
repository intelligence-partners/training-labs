#!/usr/bin/env bash
# Print the lab identifiers as export lines, and keep a copy in lab-ids.env for the cleanup.
# Load them in your shell (bash or zsh) with:
#   eval "$(./scripts/lab-env.sh)"
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require aws terraform

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
{
  echo "export AWS_REGION=$AWS_REGION"
  echo "export ACCOUNT_ID=$ACCOUNT_ID"
  echo "export BUCKET=$(tf_output bucket)"
  echo "export KB_ID=$(tf_output kb_id)"
  echo "export DS_ID=$(tf_output ds_id)"
  echo "export COLL_ARN=$(tf_output collection_arn)"
  echo "export GR_ID=$(tf_output guardrail_id)"
  echo "export GR_VERSION=$(tf_output guardrail_version)"
  echo "export PROFILE_ARN=$(tf_output profile_arn)"
  echo "export API_ID=$(tf_output api_id)"
  echo "export API_URL=$(tf_output api_url)"
} | tee "$LAB_DIR/lab-ids.env"
