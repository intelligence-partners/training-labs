#!/usr/bin/env bash
# Cleanup of the M15 lab (lesson section "Cleanup").
# Steps 1 to 7 create no billed resource: delete the virtual environment (and your clone).
# Step 8 resources (the guardrail and, if you set it up, the Policy rule) were created by infra/:
#   bash cleanup.sh                 asks for confirmation before terraform destroy
#   AUTO_APPROVE=1 bash cleanup.sh  no confirmation
set -euo pipefail
cd "$(dirname "$0")"

if [ -s infra/terraform.tfstate ]; then
  if [ -n "${AUTO_APPROVE:-}" ]; then
    terraform -chdir=infra destroy -input=false -auto-approve
  else
    terraform -chdir=infra destroy -input=false
  fi
else
  echo "No step 8 resources to destroy (infra/ was never applied)."
fi

cat <<'MSG'
Done. The Gateway and the policy engine of the AgentCore lab are not touched: keep them if you
reuse them elsewhere. Finally: deactivate the virtual environment, delete it (rm -rf .venv), and
check that no API key is left in your shell history.
MSG
