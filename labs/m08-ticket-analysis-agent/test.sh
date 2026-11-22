#!/usr/bin/env bash
# Offline checks for the M08 lab: no API key, no AWS credentials, no network call to a model.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
if [ ! -x .venv/bin/python ]; then
  "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt

echo "== solution: unit tests (Claude API and Converse mocked)"
.venv/bin/python -m pytest -q tests

echo "== starter: compiles and imports"
.venv/bin/python -m compileall -q starter
(cd starter && ANTHROPIC_API_KEY=test-key MODEL_PROVIDER= ../.venv/bin/python -c "import agent, tools, providers")

echo "OK: m08-ticket-analysis-agent"
