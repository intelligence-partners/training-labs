#!/usr/bin/env bash
# Local checks for lab m07 (also run by CI): no AWS credentials, no API key, no model download.
# - installs the test dependencies in .venv (real Chroma and rank_bm25; sentence-transformers is
#   replaced by a deterministic stand-in, so PyTorch and the two models are not needed)
# - compiles and imports the starter
# - runs the unit and end-to-end tests against solution/, every Claude call answered by a local
#   fake API and every Bedrock call by botocore's Stubber
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PYTHON_BIN="${PYTHON:-python3}"
if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements-test.txt

.venv/bin/python -m py_compile starter/*.py solution/*.py
(cd starter && PYTHONPATH=../tests/fakes ../.venv/bin/python -c \
  "import decoupage, ingestion, contextualiser, index, recherche, assistant, evaluation")
echo "Starter: compiles and imports OK"

env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_BASE_URL -u ANTHROPIC_PROFILE \
    -u AWS_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
    -u MODEL_PROVIDER -u HF_HOME \
    ANONYMIZED_TELEMETRY=False LAB_TARGET=solution \
    .venv/bin/python -m pytest -q -p no:cacheprovider tests
