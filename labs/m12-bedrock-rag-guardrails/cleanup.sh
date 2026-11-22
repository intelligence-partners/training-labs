#!/usr/bin/env bash
# Cleanup of lab M12: destroy everything the lab created, then check that nothing billable is left.
#
#   ./cleanup.sh            # destroys solution/terraform, asks for confirmation
#   ./cleanup.sh starter    # if you deployed from starter/terraform
#   ./cleanup.sh --yes      # no confirmation
#
# Terraform owns every billed resource of the lab: the HTTP API, the functions and their log
# groups, the IAM roles, the guardrail and its version, the data source, the Knowledge Base,
# the vector index, the OpenSearch Serverless collection and its three policies, the bucket and
# its documents. A Knowledge Base does NOT delete its collection: here the collection is a
# Terraform resource of its own, so destroy removes it.
#
# If you applied with -var flags, destroy with the same flags (terraform.tfvars is read
# automatically).
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

TF_DIR="$LAB_DIR/$VARIANT/terraform"
export AWS_REGION="${AWS_REGION:-eu-west-3}"
export AWS_DEFAULT_REGION="$AWS_REGION"
LAB_NAME="${LAB_NAME:-lab-rag-rh}"
KB_NAME="${KB_NAME:-kb-lab-rh}"

for cmd in terraform aws; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "error: '$cmd' is required" >&2; exit 1; }
done

# 1. Everything Terraform owns, in dependency order.
if [ -f "$TF_DIR/terraform.tfstate" ]; then
  terraform -chdir="$TF_DIR" init -input=false >/dev/null
  terraform -chdir="$TF_DIR" destroy -input=false ${AUTO_APPROVE[@]+"${AUTO_APPROVE[@]}"}
else
  echo "no Terraform state in $TF_DIR: nothing to destroy there" >&2
fi

# 2. What Terraform does not own: local files only (zips, outputs, saved identifiers).
rm -rf "$TF_DIR/build" "$LAB_DIR/$VARIANT/sortie.json" "$LAB_DIR/$VARIANT/lab-ids.env"

# 3. Check that nothing is left (a collection in DELETING state is fine).
echo
aws opensearchserverless list-collections --query 'collectionSummaries[].[name,status]' --output table
aws bedrock-agent list-knowledge-bases --query 'knowledgeBaseSummaries[].name'
aws bedrock list-guardrails --query 'guardrails[].name'

left=0
if [ -n "$(aws opensearchserverless list-collections --query "collectionSummaries[?name=='$LAB_NAME' && status!='DELETING'].name" --output text)" ]; then
  echo "LEFT: OpenSearch Serverless collection $LAB_NAME (billed per OCU-hour)" >&2
  left=1
fi
if [ -n "$(aws bedrock-agent list-knowledge-bases --query "knowledgeBaseSummaries[?name=='$KB_NAME'].knowledgeBaseId" --output text)" ]; then
  echo "LEFT: Knowledge Base $KB_NAME" >&2
  left=1
fi
if [ -n "$(aws bedrock list-guardrails --query "guardrails[?name=='$LAB_NAME'].id" --output text)" ]; then
  echo "LEFT: guardrail $LAB_NAME" >&2
  left=1
fi
if aws lambda get-function --function-name "$LAB_NAME" >/dev/null 2>&1; then
  echo "LEFT: Lambda function $LAB_NAME" >&2
  left=1
fi

if [ "$left" -eq 0 ]; then
  echo "Nothing left from the lab. Tomorrow, check in Billing that the OpenSearch Serverless line stops growing."
fi
exit "$left"
