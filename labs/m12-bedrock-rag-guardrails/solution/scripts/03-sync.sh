#!/usr/bin/env bash
# Step 3: synchronize the data source and wait for the ingestion job.
# Expected: COMPLETE, three documents scanned, three indexed, none failed (the .metadata.json
# files are counted separately).
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require aws terraform

KB_ID="${KB_ID:-$(tf_output kb_id)}"
DS_ID="${DS_ID:-$(tf_output ds_id)}"

JOB_ID=$(aws bedrock-agent start-ingestion-job --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID" \
  --query ingestionJob.ingestionJobId --output text)
echo "ingestion job $JOB_ID started" >&2

for _ in $(seq 1 60); do
  STATUS=$(aws bedrock-agent get-ingestion-job --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID" \
    --ingestion-job-id "$JOB_ID" --query ingestionJob.status --output text)
  case "$STATUS" in
    COMPLETE | FAILED | STOPPED) break ;;
    *) sleep 5 ;;
  esac
done

aws bedrock-agent get-ingestion-job --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID" \
  --ingestion-job-id "$JOB_ID" --query 'ingestionJob.[status,statistics]' --output json

[ "$STATUS" = "COMPLETE" ] || { echo "error: ingestion job ended with status $STATUS" >&2; exit 1; }
