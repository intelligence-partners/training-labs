#!/usr/bin/env bash
# Step 6: invoke the function directly, with an API Gateway-shaped event.
# Expected: statusCode 200 and a body that mentions two days a week, with teletravail.md in
# the sources.
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require aws terraform

FUNCTION_NAME="$(tf_output function_name)"
aws lambda invoke --function-name "$FUNCTION_NAME" --cli-binary-format raw-in-base64-out \
  --payload '{"body": "{\"question\": \"Combien de jours de télétravail par semaine ?\"}"}' \
  "$LAB_DIR/sortie.json" >/dev/null
cat "$LAB_DIR/sortie.json"
echo
