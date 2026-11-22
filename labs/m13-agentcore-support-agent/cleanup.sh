#!/usr/bin/env bash
# Cleanup of lab M13: destroy everything the lab created, the same day, and check that nothing
# is left.
#
#   ./cleanup.sh            # destroys the solution stacks, asks for confirmation
#   ./cleanup.sh starter    # if you deployed from starter/
#   ./cleanup.sh --yes      # no confirmation
#
# Terraform owns the runtime, its role and code bucket, the memory and its strategies, the
# Gateway, its target and role, the API key credential provider, the Policy engine and its
# policies, the online evaluation config, and the "existing API" (function, HTTP API, role, log
# group). What AgentCore creates on its own is deleted after the destroy: the runtime's log
# groups and the evaluation results log group. CloudWatch Transaction Search is an account-level
# setting and stays enabled (see the end of this script).
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VARIANT="solution"
AUTO_APPROVE=()
for arg in "$@"; do
  case "$arg" in
    solution | starter) VARIANT="$arg" ;;
    -y | --yes) AUTO_APPROVE=(-auto-approve) ;;
    -h | --help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *)
      echo "unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

ROOT="$LAB_DIR/$VARIANT"
TF_API_DIR="$ROOT/terraform/acme-api"
TF_AGENT_DIR="$ROOT/terraform/support-agent"
export AWS_REGION="${AWS_REGION:-eu-west-3}"
export AWS_DEFAULT_REGION="$AWS_REGION"
PROJECT_NAME="${PROJECT_NAME:-supportlab}"

for cmd in terraform aws; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "error: '$cmd' is required" >&2; exit 1; }
done

# Destroy needs the variables that have no default. The key is not used to delete anything.
if [ -z "${TF_VAR_acme_api_key:-}" ]; then
  if [ -f "$ROOT/.acme-api-key" ]; then
    TF_VAR_acme_api_key="$(cat "$ROOT/.acme-api-key")"
  else
    TF_VAR_acme_api_key="destroy-only-placeholder-0000000000000000"
  fi
  export TF_VAR_acme_api_key
fi
if [ -z "${TF_VAR_acme_api_url:-}" ]; then
  TF_VAR_acme_api_url="$(terraform -chdir="$TF_API_DIR" output -raw api_url 2>/dev/null || echo "https://placeholder.invalid")"
  export TF_VAR_acme_api_url
fi

destroy() {
  local dir="$1"
  if [ -f "$dir/terraform.tfstate" ]; then
    terraform -chdir="$dir" init -input=false >/dev/null
    terraform -chdir="$dir" destroy -input=false ${AUTO_APPROVE[@]+"${AUTO_APPROVE[@]}"}
  else
    echo "no Terraform state in $dir: nothing to destroy there" >&2
  fi
}

# Identifiers needed after the destroy, to find the log groups AgentCore created.
RUNTIME_ID="$(terraform -chdir="$TF_AGENT_DIR" output -raw runtime_id 2>/dev/null || true)"
EVAL_LOG_GROUP="$(terraform -chdir="$TF_AGENT_DIR" output -raw online_eval_log_group 2>/dev/null || true)"
EVAL_ID="$(terraform -chdir="$TF_AGENT_DIR" output -raw online_eval_config_id 2>/dev/null || true)"
if [ -z "$EVAL_LOG_GROUP" ] && [ -n "$EVAL_ID" ]; then
  # Default results log group of an online evaluation config (AgentCore CLI convention).
  EVAL_LOG_GROUP="/aws/bedrock-agentcore/evaluations/results/$EVAL_ID"
fi

# 1. The agent stack first (it uses the API), then the existing API.
destroy "$TF_AGENT_DIR"
destroy "$TF_API_DIR"

# 2. What Terraform does not own: log groups created by the service, local files.
delete_log_groups() {
  local prefix="$1" name
  for name in $(aws logs describe-log-groups --log-group-name-prefix "$prefix" \
    --query 'logGroups[].logGroupName' --output text); do
    echo "deleting log group $name"
    aws logs delete-log-group --log-group-name "$name"
  done
}
if [ -n "$RUNTIME_ID" ]; then
  delete_log_groups "/aws/bedrock-agentcore/runtimes/$RUNTIME_ID"
fi
if [ -n "$EVAL_LOG_GROUP" ]; then
  delete_log_groups "$EVAL_LOG_GROUP"
fi
rm -rf "$ROOT/build" "$ROOT/terraform/acme-api/build"
rm -f "$ROOT/.acme-api-key"

# 3. Check that nothing is left.
echo
aws bedrock-agentcore-control list-agent-runtimes --query 'agentRuntimes[].agentRuntimeName'
aws bedrock-agentcore-control list-gateways --query 'items[].name'
aws bedrock-agentcore-control list-memories --query 'memories[].id'
aws bedrock-agentcore-control list-policy-engines --query 'policyEngines[].name'
aws bedrock-agentcore-control list-api-key-credential-providers --query 'credentialProviders[].name'
aws logs describe-log-groups --log-group-name-prefix /aws/bedrock-agentcore --query 'logGroups[].logGroupName'

left=0
check_absent() {
  local what="$1" found="$2"
  if [ -n "$found" ]; then
    echo "LEFT: $what: $found" >&2
    left=1
  fi
}
check_absent "runtime" "$(aws bedrock-agentcore-control list-agent-runtimes --query "agentRuntimes[?starts_with(agentRuntimeName, '${PROJECT_NAME}_')].agentRuntimeName" --output text)"
check_absent "gateway" "$(aws bedrock-agentcore-control list-gateways --query "items[?starts_with(name, '${PROJECT_NAME//_/-}-')].name" --output text)"
check_absent "memory" "$(aws bedrock-agentcore-control list-memories --query "memories[?starts_with(id, '${PROJECT_NAME}_')].id" --output text)"
check_absent "policy engine" "$(aws bedrock-agentcore-control list-policy-engines --query "policyEngines[?starts_with(name, '${PROJECT_NAME}_')].name" --output text)"
check_absent "API key provider" "$(aws bedrock-agentcore-control list-api-key-credential-providers --query "credentialProviders[?starts_with(name, '${PROJECT_NAME//_/-}-')].name" --output text)"
if aws lambda get-function --function-name acme-support-api >/dev/null 2>&1; then
  check_absent "Lambda function" "acme-support-api"
fi

cat <<EOF

CloudWatch Transaction Search stays enabled for the account in $AWS_REGION. Indexing beyond the
free tier is billed: when you no longer need it, lower the indexed percentage, for example:
  aws xray update-indexing-rule --name Default --rule '{"Probabilistic":{"DesiredSamplingPercentage":1}}'
The CDK bootstrap stack (CDKToolkit) is not used by this Terraform version of the lab.
EOF
exit "$left"
