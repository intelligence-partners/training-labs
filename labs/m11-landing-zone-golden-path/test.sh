#!/usr/bin/env bash
# Offline checks of lab M11. No AWS account, no credentials, no AWS call: the
# plans run against a local stub (see tests/tfplan.py).
#
#   bash test.sh                       # checks the solution (and that the starter is valid)
#   LAB_TARGET=starter bash test.sh    # also runs the tests against your work in starter/
#
# Requires: Terraform >= 1.5.7 and Python >= 3.10 on the PATH.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$LAB_DIR"
TARGET="${LAB_TARGET:-solution}"

# Never pick up real credentials, even on a machine that has some.
unset AWS_PROFILE AWS_DEFAULT_PROFILE AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
export AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_EC2_METADATA_DISABLED=true
export TF_IN_AUTOMATION=1 CHECKPOINT_DISABLE=1
# Download each provider once for all the Terraform folders of the lab.
export TF_PLUGIN_CACHE_DIR="${TF_PLUGIN_CACHE_DIR:-$LAB_DIR/.terraform-plugin-cache}"
export TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE=true
mkdir -p "$TF_PLUGIN_CACHE_DIR"

step() { printf '\n==> %s\n' "$*"; }

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform not found: install Terraform 1.5.7 or later." >&2
  exit 1
fi
PYTHON="${PYTHON:-$(command -v python3.13 || command -v python3.12 || command -v python3)}"
terraform version | head -n 1
"$PYTHON" --version

step "Python virtual environment (.venv) and test dependencies"
if [ ! -x .venv/bin/python ]; then
  "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r tests/requirements.txt

step "Terraform: formatting (terraform fmt -check -recursive)"
for dir in solution starter; do
  terraform fmt -check -recursive -diff "$dir"
done

for project in solution starter; do
  for dir in infra/landing-zone infra/assistant-rh infra/modules/ai-service-baseline; do
    step "Terraform: init and validate $project/$dir"
    terraform -chdir="$project/$dir" init -backend=false -input=false -no-color >/dev/null
    terraform -chdir="$project/$dir" validate -no-color
  done
done

step "Python: the guardrail compiles (starter and solution)"
.venv/bin/python -m py_compile starter/guardrails/require_kms_encrypted_buckets.py solution/guardrails/require_kms_encrypted_buckets.py

step "Offline terraform plans: landing zone, golden path, guardrails ($TARGET)"
LAB_TARGET="$TARGET" .venv/bin/python -m pytest -q -p no:cacheprovider tests

step "All M11 checks passed ($TARGET)"
