#!/usr/bin/env bash
# Step 7: ask the HTTP API a question.
#   ./scripts/07-ask.sh "Combien de jours de télétravail par semaine ?"
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require curl jq terraform

QUESTION="${1:-Combien de jours de télétravail par semaine ?}"
API_URL="${API_URL:-$(tf_output api_url)}"

curl -s -X POST "$API_URL" -H "Content-Type: application/json" \
  -d "$(jq -cn --arg q "$QUESTION" '{question: $q}')"
echo
