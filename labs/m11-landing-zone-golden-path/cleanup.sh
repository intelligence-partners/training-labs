#!/usr/bin/env bash
# Cleanup of lab M11: deletes everything the lab created, in the lesson's order.
#
#   bash cleanup.sh [PROJECT_DIR] [--yes] [--disable-scp] [--delete-organization]
#
# PROJECT_DIR      folder that holds infra/ (default: ./solution next to this script)
# --yes            skip Terraform's confirmation prompts
# --disable-scp    also disable the SCP policy type on the root (optional step 4)
# --delete-organization
#                  also delete the test organization, if it has no member account
#                  (optional step 5; implies --disable-scp)
#
# Run it from the management account of the TEST organization, with the same
# profile as the lab. TF_VAR_root_id is looked up if it is not set.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$LAB_DIR/solution"
AUTO_APPROVE=()
DISABLE_SCP=false
DELETE_ORG=false
for arg in "$@"; do
  case "$arg" in
    --yes) AUTO_APPROVE=(-auto-approve) ;;
    --disable-scp) DISABLE_SCP=true ;;
    --delete-organization) DELETE_ORG=true; DISABLE_SCP=true ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) PROJECT_DIR="$(cd "$arg" && pwd)" ;;
  esac
done
GOLDEN_PATH="$PROJECT_DIR/infra/assistant-rh"
LANDING_ZONE="$PROJECT_DIR/infra/landing-zone"
export AWS_REGION="${AWS_REGION:-eu-west-3}"

for tool in terraform aws; do
  command -v "$tool" >/dev/null 2>&1 || { echo "$tool not found." >&2; exit 1; }
done
[ -d "$GOLDEN_PATH" ] && [ -d "$LANDING_ZONE" ] || { echo "No infra/ folder in $PROJECT_DIR." >&2; exit 1; }

echo "Account and identity used for the cleanup:"
aws sts get-caller-identity --output table
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export TF_VAR_root_id="${TF_VAR_root_id:-$(aws organizations list-roots --query 'Roots[0].Id' --output text)}"
# Destroy does not use the address; any valid value lets Terraform evaluate the configuration.
export TF_VAR_budget_email="${TF_VAR_budget_email:-cleanup@example.com}"
failed=0

# 1. The golden path: the bucket is emptied (force_destroy, every version), the
#    log group and the budget are deleted, the key enters a 7-day pending deletion.
terraform -chdir="$GOLDEN_PATH" init -input=false -no-color >/dev/null
KEY_ID="$(terraform -chdir="$GOLDEN_PATH" output -raw kms_key_id 2>/dev/null || true)"
BUCKET="$(terraform -chdir="$GOLDEN_PATH" output -raw bucket_name 2>/dev/null || true)"
terraform -chdir="$GOLDEN_PATH" destroy -input=false ${AUTO_APPROVE[@]+"${AUTO_APPROVE[@]}"}

if [ -n "$KEY_ID" ]; then
  state="$(aws kms describe-key --key-id "$KEY_ID" --query 'KeyMetadata.[KeyState,DeletionDate]' --output text)"
  echo "KMS key $KEY_ID: $state"
  case "$state" in PendingDeletion*) ;; *) echo "The key is not pending deletion." >&2; failed=1 ;; esac
fi
if [ -n "$BUCKET" ] && aws s3api head-bucket --bucket "$BUCKET" >/dev/null 2>&1; then
  echo "Bucket $BUCKET still exists." >&2; failed=1
fi
if [ -n "$(aws logs describe-log-groups --log-group-name-prefix /socle-ia/ --query 'logGroups[].logGroupName' --output text)" ]; then
  echo "A /socle-ia/ log group still exists." >&2; failed=1
fi
if aws budgets describe-budget --account-id "$ACCOUNT_ID" --budget-name assistant-rh-mensuel >/dev/null 2>&1; then
  echo "Budget assistant-rh-mensuel still exists." >&2; failed=1
fi

# 2. The landing zone: the SCPs are detached and deleted, then the empty OUs.
terraform -chdir="$LANDING_ZONE" init -input=false -no-color >/dev/null
terraform -chdir="$LANDING_ZONE" destroy -input=false ${AUTO_APPROVE[@]+"${AUTO_APPROVE[@]}"}

ous="$(aws organizations list-organizational-units-for-parent --parent-id "$TF_VAR_root_id" \
  --query 'OrganizationalUnits[].Name' --output text)"
if [ -n "$ous" ]; then
  echo "OUs still under the root: $ous" >&2; failed=1
fi
scps="$(aws organizations list-policies --filter SERVICE_CONTROL_POLICY --query 'Policies[].Name' --output text)"
for name in DenyLeaveOrganization DenyOutsideAllowedRegions ProtectSecurityBaseline DenyIamUsers; do
  if printf '%s\n' $scps | grep -qx "$name"; then
    echo "SCP $name still exists." >&2; failed=1
  fi
done

# 3. What Terraform does not own: what step 1 created with the CLI.
if [ "$DISABLE_SCP" = true ]; then
  aws organizations disable-policy-type --root-id "$TF_VAR_root_id" --policy-type SERVICE_CONTROL_POLICY >/dev/null
  echo "SCP policy type disabled on $TF_VAR_root_id."
fi
if [ "$DELETE_ORG" = true ]; then
  members="$(aws organizations list-accounts --query 'length(Accounts)' --output text)"
  if [ "$members" = "1" ]; then
    aws organizations delete-organization
    echo "Organization deleted."
  else
    echo "The organization has $members accounts: not deleted. Remove the member accounts first." >&2
    failed=1
  fi
fi
rm -f "$PROJECT_DIR/plan.json" "$GOLDEN_PATH/tfplan" "$LANDING_ZONE/tfplan"

if [ "$failed" -ne 0 ]; then
  echo "Cleanup incomplete: see the messages above." >&2
  exit 1
fi
echo "Cleanup complete. The KMS key is deleted for good at the end of its waiting period."
