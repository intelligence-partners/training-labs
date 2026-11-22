#!/usr/bin/env bash
# Offline checks for the M14 lab: no AWS credentials, no model call, no resource created.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
if [ ! -x .venv/bin/python ]; then
  "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt

echo "== solution: unit tests (Bedrock, CloudWatch and spans mocked)"
.venv/bin/python -m pytest -q tests

echo "== starter: compiles and imports"
.venv/bin/python -m compileall -q starter
(cd starter && AWS_REGION=eu-west-3 AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing MODEL_PROVIDER= \
  ../.venv/bin/python -c "import agent, providers")

echo "== shell scripts: syntax"
bash -n cleanup.sh

if [ -n "${SKIP_TERRAFORM:-}" ]; then
  echo "== infra: Terraform checks skipped (SKIP_TERRAFORM is set)"
else
  command -v terraform >/dev/null || { echo "terraform is required (or set SKIP_TERRAFORM=1)" >&2; exit 1; }
  echo "== infra: terraform fmt, init -backend=false, validate"
  terraform -chdir=infra fmt -check -recursive
  terraform -chdir=infra init -backend=false -input=false >/dev/null
  terraform -chdir=infra validate -no-color
fi

echo "OK: m14-llmops-cost-quality-dashboard"
