#!/usr/bin/env bash
# Step 0: check that the inference profile exists, where it routes, and that the model answers.
# Expected: the foundation-model ARNs in EU Regions, then "OK". An AccessDeniedException means
# model access is not complete (Marketplace permissions, Anthropic use case form).
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require aws

aws bedrock get-inference-profile --inference-profile-identifier "$MODEL_ID" \
  --query 'models[].modelArn' --output text

# First call: it validates model access (and starts the subscription if needed).
aws bedrock-runtime converse --model-id "$MODEL_ID" \
  --messages '[{"role":"user","content":[{"text":"Réponds simplement : OK"}]}]' \
  --inference-config '{"maxTokens":256}' \
  --query 'output.message.content[?text].text' --output text
