#!/usr/bin/env bash
# Offline checks for the M15 lab: no API key, no AWS credentials, no network call to a model.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
if [ ! -x .venv/bin/python ]; then
  "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt

echo "== solution: unit tests (Claude API, Converse and Guardrails mocked)"
.venv/bin/python -m pytest -q tests

echo "== starter: compiles and imports"
.venv/bin/python -m compileall -q starter
(cd starter && ANTHROPIC_API_KEY=test-key MODEL_PROVIDER= ../.venv/bin/python -c "import agent, banc, garde, outils, providers")

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

echo "OK: m15-agent-red-team"
