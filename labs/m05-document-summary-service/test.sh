#!/usr/bin/env bash
# Local checks for lab m05 (also run by CI): no AWS credentials, no API key, no network to Claude.
# - installs the Python dependencies in .venv and the Node dependencies of the TypeScript variant
# - type-checks the TypeScript variant (both editions, solution and starter)
# - compiles and imports the starters
# - runs the unit and end-to-end tests against solution/ (French edition) and solution-en/
#   (English edition), every model call answered by a local fake API
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PYTHON_BIN="${PYTHON:-python3}"
if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt

for dir in solution/ts starter/ts solution-en/ts starter-en/ts; do
  (cd "$dir" && npm ci --no-audit --no-fund --loglevel=error)
  (cd "$dir" && ./node_modules/.bin/tsc -p .)
done
echo "TypeScript: type check OK (solution, starter, solution-en, starter-en)"

.venv/bin/python -m py_compile starter/*.py solution/*.py starter-en/*.py solution-en/*.py
for dir in starter starter-en; do
  (cd "$dir" && ../.venv/bin/python -c "import schema, fichiers, service, main")
done
echo "Starters: compile and import OK"

# Scrub real credentials so a test can never reach the real API by accident.
for target in solution solution-en; do
  echo "Tests: $target"
  env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_BASE_URL -u ANTHROPIC_PROFILE \
      -u AWS_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
      LAB_REQUIRE_NODE=1 LAB_TARGET="$target" \
      .venv/bin/python -m pytest -q -p no:cacheprovider tests
done
