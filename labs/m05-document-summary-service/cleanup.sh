#!/usr/bin/env bash
# Cleanup for lab m05 (lesson "Nettoyage" section).
#
# The lab creates no AWS resource. It leaves PDFs in the Files API of your Claude
# workspace, listed in the local index .fichiers.json; they persist until deleted.
# This script deletes every file_id of that index, then the index itself.
#
# Usage: bash cleanup.sh [DIR]   (DIR = the folder where you ran main.py; default: current folder)
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-$PWD}"
PYTHON="${LAB_DIR}/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"

cd "$TARGET"
if [ ! -f .fichiers.json ]; then
  echo "No .fichiers.json index in $(pwd): nothing to delete in the Files API."
else
  "$PYTHON" - <<'EOF'
import json
import pathlib

import anthropic

client = anthropic.Anthropic()
index = pathlib.Path(".fichiers.json")
for file_id in json.loads(index.read_text()).values():
    try:
        client.files.delete(file_id)
        print("deleted", file_id)
    except anthropic.NotFoundError:
        print("already gone", file_id)
index.unlink()
EOF
fi

cat <<'EOF'
TypeScript variant: it uploads the PDF on every run. List your files with client.files.list()
and delete the ones named after your PDF.
If you created an API key just for this lab, revoke it in the Claude Console.
With MODEL_PROVIDER=bedrock nothing is created: the PDF travels inside the request.
EOF
