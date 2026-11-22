# shellcheck shell=bash
# Helpers shared by the scripts of lab M13. Sourced, never run directly.
# shellcheck disable=SC2034  # the variables are used by the scripts that source this file

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_API_DIR="$LAB_DIR/terraform/acme-api"
TF_AGENT_DIR="$LAB_DIR/terraform/support-agent"
AGENT_SRC="$LAB_DIR/SupportLab/app/agent"
BUILD_DIR="$LAB_DIR/build"
export AWS_REGION="${AWS_REGION:-eu-west-3}"
export AWS_DEFAULT_REGION="$AWS_REGION"

require() {
  local cmd
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "error: '$cmd' is required" >&2; exit 1; }
  done
}

api_output() {
  terraform -chdir="$TF_API_DIR" output -raw "$1"
}

agent_output() {
  terraform -chdir="$TF_AGENT_DIR" output -raw "$1"
}
