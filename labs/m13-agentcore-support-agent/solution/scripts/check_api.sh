#!/usr/bin/env bash
# Step 1: call the existing API without, then with the key.
# Expected:
#   401
#   {"orderId": "A-1042", "status": "expédiée", "carrier": "Colissimo", "totalCents": 18990}
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require curl terraform

API_URL="${API_URL:-$(api_output api_url)}"
if [ -z "${ACME_API_KEY:-}" ]; then
  ACME_API_KEY="$(cat "$LAB_DIR/.acme-api-key")"
fi

curl -s -o /dev/null -w "%{http_code}\n" "$API_URL/orders/A-1042"
curl -s -H "x-api-key: $ACME_API_KEY" "$API_URL/orders/A-1042"
echo
