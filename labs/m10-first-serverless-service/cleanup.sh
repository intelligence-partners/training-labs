#!/usr/bin/env bash
# Cleanup of lab M10: deletes everything the lab created in your AWS account.
#
#   bash cleanup.sh [PROJECT_DIR] [--yes]
#
# PROJECT_DIR is the folder that holds infra/ and src/ (default: ./solution next
# to this script). --yes skips Terraform's confirmation prompt.
# Uses your current AWS_PROFILE; the Region is eu-west-3 unless AWS_REGION says otherwise.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$LAB_DIR/solution"
AUTO_APPROVE=()
for arg in "$@"; do
  case "$arg" in
    --yes) AUTO_APPROVE=(-auto-approve) ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) PROJECT_DIR="$(cd "$arg" && pwd)" ;;
  esac
done
INFRA="$PROJECT_DIR/infra"
REGION="${AWS_REGION:-eu-west-3}"
export AWS_REGION="$REGION"

for tool in terraform aws; do
  command -v "$tool" >/dev/null 2>&1 || { echo "$tool not found." >&2; exit 1; }
done
[ -d "$INFRA" ] || { echo "No infra/ folder in $PROJECT_DIR." >&2; exit 1; }

echo "Account and identity used for the cleanup:"
aws sts get-caller-identity --output table

terraform -chdir="$INFRA" init -input=false -no-color >/dev/null
# Read the names before destroying: the outputs disappear with the resources.
FUNCTION_NAME="$(terraform -chdir="$INFRA" output -raw function_name 2>/dev/null || echo registre-prompts-prompts)"
TABLE_NAME="$(terraform -chdir="$INFRA" output -raw table_name 2>/dev/null || echo registre-prompts)"

# 1. Everything Terraform created: table and data, function, API, role, log group.
terraform -chdir="$INFRA" destroy -input=false ${AUTO_APPROVE[@]+"${AUTO_APPROVE[@]}"}

# 2. Verification: each command must report that the resource no longer exists.
failed=0
if aws lambda get-function --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then
  echo "Function $FUNCTION_NAME still exists." >&2; failed=1
fi
if aws dynamodb describe-table --table-name "$TABLE_NAME" >/dev/null 2>&1; then
  echo "Table $TABLE_NAME still exists." >&2; failed=1
fi
groups="$(aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/$FUNCTION_NAME" \
  --query 'logGroups[].logGroupName' --output text)"
if [ -n "$groups" ]; then
  echo "Log groups still present: $groups" >&2; failed=1
fi

# 3. What Terraform does not own: the local build artifact and saved plan.
#    (The execution role cannot create log groups, so Lambda created none outside Terraform.)
rm -rf "$INFRA/.build" "$INFRA/tfplan"

if [ "$failed" -ne 0 ]; then
  echo "Cleanup incomplete: run the script again, or delete the resources above from the console." >&2
  exit 1
fi
echo "Cleanup complete: no resource of the lab remains in $REGION."
