#!/usr/bin/env bash
# Offline checks of lab M12. No AWS credentials and no API key are needed: every AWS call of the
# unit tests is stubbed, and Terraform is only initialized (no backend) and validated.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$LAB_DIR"

PYTHON="${PYTHON:-$(command -v python3.12 || command -v python3)}"

echo "== Python environment (.venv, pinned versions)"
[ -x .venv/bin/python ] || "$PYTHON" -m venv .venv
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt

echo "== Unit tests (Retrieve, Converse and OpenSearch calls stubbed)"
.venv/bin/python -m pytest -q

echo "== Shell scripts (bash -n, shellcheck)"
scripts=(cleanup.sh test.sh solution/scripts/*.sh starter/scripts/*.sh)
for script in "${scripts[@]}"; do
  bash -n "$script"
done
.venv/bin/shellcheck -x -P SCRIPTDIR "${scripts[@]}"

echo "== Terraform (fmt, init without backend, validate)"
command -v terraform >/dev/null 2>&1 || { echo "error: terraform is required (>= 1.5.7)" >&2; exit 1; }
export TF_IN_AUTOMATION=1
export TF_PLUGIN_CACHE_DIR="${TF_PLUGIN_CACHE_DIR:-$LAB_DIR/.terraform-plugin-cache}"
mkdir -p "$TF_PLUGIN_CACHE_DIR"
terraform fmt -check -recursive
for dir in solution/terraform starter/terraform; do
  terraform -chdir="$dir" init -backend=false -input=false -lockfile=readonly >/dev/null
  terraform -chdir="$dir" validate -no-color
done

echo "All offline checks passed."
