#!/usr/bin/env bash
# Cleanup for lab m07 (lesson "Nettoyage" section).
#
# The lab creates no AWS resource and no recurring cost. This script frees the disk space:
# - the Chroma index (./index) and chunks.jsonl in the folder where you ran the lab;
# - the two local models downloaded from Hugging Face (about 470 MB each).
# The code, the corpus and the lab's .venv are kept: delete the repository folder, or
# `rm -rf .venv` in this lab, when you no longer need them.
#
# Usage: bash cleanup.sh [DIR]   (DIR = the folder where you ran the lab; default: current folder)
set -euo pipefail

TARGET="${1:-$PWD}"
HUB="${HF_HOME:-$HOME/.cache/huggingface}/hub"

for path in "$TARGET/index" "$TARGET/chunks.jsonl"; do
  if [ -e "$path" ]; then
    rm -rf "$path"
    echo "removed $path"
  fi
done

for model in models--intfloat--multilingual-e5-small models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1; do
  if [ -d "$HUB/$model" ]; then
    rm -rf "${HUB:?}/$model"
    echo "removed $HUB/$model"
  fi
done

echo "If you created an API key just for this lab, disable it in the Claude Console."
