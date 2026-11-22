#!/usr/bin/env bash
# Step 4: check retrieval before plugging the model in.
# Expected: notes-de-frais.md first for the first query; only securite-informatique.md for the
# second, thanks to the filter on the "service" metadata.
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require aws terraform

KB_ID="${KB_ID:-$(tf_output kb_id)}"

aws bedrock-agent-runtime retrieve --knowledge-base-id "$KB_ID" \
  --retrieval-query text="Quel est le plafond de remboursement d'un repas ?" \
  --query 'retrievalResults[].{score:score,source:location.s3Location.uri}' --output table

aws bedrock-agent-runtime retrieve --knowledge-base-id "$KB_ID" \
  --retrieval-query text="Règles de mot de passe" \
  --retrieval-configuration '{"vectorSearchConfiguration":{"numberOfResults":3,"filter":{"equals":{"key":"service","value":"DSI"}}}}' \
  --query 'retrievalResults[].location.s3Location.uri' --output text
