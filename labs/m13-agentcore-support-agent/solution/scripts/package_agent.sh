#!/usr/bin/env bash
# Build the CodeZip artifact of the runtime (build/agent.zip), the way `agentcore deploy` does
# for a CodeZip runtime: install the locked dependencies for Linux arm64, the platform of
# AgentCore Runtime, then add the agent code. No Docker needed.
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require uv zip tar

# Must match the runtime version in terraform/support-agent/runtime.tf (PYTHON_3_12).
PYTHON_VERSION="3.12"
# AgentCore Runtime runs Amazon Linux 2023 (glibc 2.34): any manylinux tag up to 2_34 works.
PLATFORMS=(aarch64-manylinux2014 aarch64-manylinux_2_28 aarch64-manylinux_2_34)
MAX_ZIP_BYTES=$((250 * 1024 * 1024))
STAGING="$BUILD_DIR/agent"
ZIP="$BUILD_DIR/agent.zip"

installed=""
for platform in "${PLATFORMS[@]}"; do
  rm -rf "$STAGING"
  mkdir -p "$STAGING"
  if uv pip install --quiet --target "$STAGING" --python-version "$PYTHON_VERSION" \
    --python-platform "$platform" --only-binary :all: -r "$AGENT_SRC/requirements.txt"; then
    installed="$platform"
    break
  fi
  echo "no complete set of wheels for $platform, trying the next platform" >&2
done
[ -n "$installed" ] || { echo "error: dependency installation failed for every platform" >&2; exit 1; }

# The agent code, without local environments and caches.
(cd "$AGENT_SRC" && tar -cf - --exclude=.git --exclude=.venv --exclude=__pycache__ \
  --exclude=.pytest_cache --exclude=.DS_Store --exclude=node_modules .) | (cd "$STAGING" && tar -xf -)

# Console scripts carry the shebang of the build machine: rewrite the ones the entry point uses.
write_console_script() {
  local name="$1" module="$2" function="$3"
  [ -f "$STAGING/bin/$name" ] || return 0
  cat >"$STAGING/bin/$name" <<EOF
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
from $module import $function
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\\.pyw|\\.exe)?\$', '', sys.argv[0])
    sys.exit($function())
EOF
  chmod 755 "$STAGING/bin/$name"
}
write_console_script opentelemetry-instrument opentelemetry.instrumentation.auto_instrumentation run
write_console_script opentelemetry-bootstrap opentelemetry.instrumentation.bootstrap run

# Fixed timestamps: the same sources give the same zip, so Terraform only updates the runtime
# when something changed.
find "$STAGING" -exec touch -h -t 198001020000 {} +
rm -f "$ZIP"
(cd "$STAGING" && zip -qrX "$ZIP" .)

size=$(wc -c <"$ZIP" | tr -d ' ')
[ "$size" -le "$MAX_ZIP_BYTES" ] || { echo "error: $ZIP is $size bytes, above the 250 MB limit" >&2; exit 1; }
echo "built $ZIP ($((size / 1024 / 1024)) MB, wheels for $installed)"
