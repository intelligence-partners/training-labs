# shellcheck shell=bash
# Helpers shared by the step scripts. Sourced, never run directly.

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$LAB_DIR/terraform"
export AWS_REGION="${AWS_REGION:-eu-west-3}"
export AWS_DEFAULT_REGION="$AWS_REGION"
MODEL_ID="${MODEL_ID:-eu.anthropic.claude-opus-5-5}"

require() {
  local cmd
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "error: '$cmd' is required" >&2; exit 1; }
  done
}

# Read one Terraform output of the lab.
tf_output() {
  terraform -chdir="$TF_DIR" output -raw "$1"
}
