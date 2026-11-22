#!/usr/bin/env bash
# Enable CloudWatch Transaction Search once per account and Region, as `agentcore deploy` does:
# the runtime's spans then land in the aws/spans log group, which traces (step 9) and online
# evaluation (step 10) read.
#
# This is an account-level setting, deliberately kept out of Terraform: destroying the lab must
# not switch it off for other workloads. Indexing beyond the free tier is billed; lower the
# percentage when you no longer need it (see cleanup.sh).
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require aws jq

POLICY_NAME="TransactionSearchXRayAccess"
INDEX_PERCENTAGE="${INDEX_PERCENTAGE:-100}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

read -r destination status < <(aws xray get-trace-segment-destination --query '[Destination,Status]' --output text)
if [ "$destination" = "CloudWatchLogs" ] && [ "$status" = "ACTIVE" ]; then
  echo "Transaction Search is already enabled in $AWS_REGION."
  exit 0
fi

aws application-signals start-discovery

existing="$(aws logs describe-resource-policies \
  --query "resourcePolicies[?policyName=='$POLICY_NAME'].policyName" --output text)"
if [ -z "$existing" ]; then
  policy="$(jq -cn --arg region "$AWS_REGION" --arg account "$ACCOUNT_ID" --arg sid "$POLICY_NAME" '{
    Version: "2012-10-17",
    Statement: [{
      Sid: $sid,
      Effect: "Allow",
      Principal: {Service: "xray.amazonaws.com"},
      Action: "logs:PutLogEvents",
      Resource: [
        "arn:aws:logs:\($region):\($account):log-group:aws/spans:*",
        "arn:aws:logs:\($region):\($account):log-group:/aws/application-signals/data:*"
      ],
      Condition: {
        ArnLike: {"aws:SourceArn": "arn:aws:xray:\($region):\($account):*"},
        StringEquals: {"aws:SourceAccount": $account}
      }
    }]
  }')"
  aws logs put-resource-policy --policy-name "$POLICY_NAME" --policy-document "$policy" >/dev/null
fi

aws xray update-trace-segment-destination --destination CloudWatchLogs >/dev/null
aws xray update-indexing-rule --name Default \
  --rule "{\"Probabilistic\":{\"DesiredSamplingPercentage\":$INDEX_PERCENTAGE}}" >/dev/null
echo "Transaction Search enabled in $AWS_REGION (indexing $INDEX_PERCENTAGE% of spans). It can take a few minutes to become ACTIVE."
