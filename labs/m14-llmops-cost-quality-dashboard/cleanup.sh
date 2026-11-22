#!/usr/bin/env bash
# Cleanup of the M14 lab (lesson section "Cleanup"): removes everything infra/ created.
#   bash cleanup.sh                 asks for confirmation before terraform destroy
#   AUTO_APPROVE=1 bash cleanup.sh  no confirmation
set -euo pipefail
cd "$(dirname "$0")"

region="$(terraform -chdir=infra output -raw region 2>/dev/null || echo "${AWS_REGION:-eu-west-3}")"
managed_ts="$(terraform -chdir=infra output -raw transaction_search_managed_by_lab 2>/dev/null || echo false)"

# Budget, three alarms, dashboard, SNS topic (deleting the topic deletes its subscription),
# invocation logging configuration, /m14/bedrock-invocations log group, m14-bedrock-logs role
# and, if the lab created it, the m14-transaction-search resource policy.
if [ -n "${AUTO_APPROVE:-}" ]; then
  terraform -chdir=infra destroy -input=false -auto-approve
else
  terraform -chdir=infra destroy -input=false
fi

# Only if this lab enabled Transaction Search (step 4): Terraform does not switch X-Ray back.
if [ "$managed_ts" = "true" ]; then
  aws xray update-trace-segment-destination --destination XRay --region "$region"
  aws logs delete-log-group --log-group-name aws/spans --region "$region" || true
fi

# If a Bedrock logging configuration existed before the lab, restore it instead of leaving none.
previous="infra/previous-logging-config.json"
if [ -s "$previous" ] && [ "$(tr -d '[:space:]' < "$previous")" != "null" ]; then
  aws bedrock put-model-invocation-logging-configuration --logging-config "file://$previous" --region "$region"
  echo "Restored the previous Bedrock invocation logging configuration from $previous."
fi

cat <<'MSG'
Done. The M14/AgentSupport custom metrics cannot be deleted: they stop being fed, their hourly
billing stops, and they disappear from the console on their own.
Finally: deactivate the virtual environment and delete it (rm -rf .venv).
MSG
