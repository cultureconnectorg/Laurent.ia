#!/usr/bin/env bash
# Downloads open-weight model files ONCE into deploy/models and verifies them against
# the SHA-256 published by the model repository. Only public files are downloaded:
# no data about you is sent. After this, the engine runs without any network.
# Usage: scripts/fetch-model.sh [desktop|laptop|test]
#   desktop  Qwen2.5-7B-Instruct, Q4_K_M  (~4.7 GB, 8+ GB RAM)   Apache-2.0
#   laptop   Qwen2.5-1.5B-Instruct, Q4_K_M (~1.1 GB, 4+ GB RAM)  Apache-2.0
#   test     Qwen2.5-0.5B-Instruct, Q4_K_M (~0.4 GB)             Apache-2.0
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-desktop}" in
  desktop) REPO=Qwen/Qwen2.5-7B-Instruct-GGUF;   ALIAS=qwen2.5-7b-instruct ;;
  laptop)  REPO=Qwen/Qwen2.5-1.5B-Instruct-GGUF; ALIAS=qwen2.5-1.5b-instruct ;;
  test)    REPO=Qwen/Qwen2.5-0.5B-Instruct-GGUF; ALIAS=qwen2.5-0.5b-instruct ;;
  *) echo "profile: desktop | laptop | test"; exit 2 ;;
esac
mkdir -p models
# Publisher metadata: file names and SHA-256 of every q4_k_m file (single or split).
python3 - "$REPO" > models/.manifest <<'PY'
import json, sys, urllib.request
repo = sys.argv[1]
with urllib.request.urlopen(f"https://huggingface.co/api/models/{repo}/tree/main") as r:
    files = json.load(r)
for f in sorted(files, key=lambda f: f["path"]):
    if f["path"].lower().endswith(".gguf") and "q4_k_m" in f["path"].lower():
        print(f["path"], f["lfs"]["oid"])
PY
[ -s models/.manifest ] || { echo "no Q4_K_M file found in $REPO"; exit 1; }
FIRST=""
while read -r name sha; do
  [ -z "$FIRST" ] && FIRST=$name
  if [ ! -f "models/$name" ] || ! echo "$sha  models/$name" | sha256sum -c --status; then
    echo "downloading $name"
    curl -fL --retry 3 -o "models/$name.part" "https://huggingface.co/$REPO/resolve/main/$name"
    mv "models/$name.part" "models/$name"
  fi
  echo "$sha  models/$name" | sha256sum -c -
done < models/.manifest
cp models/.manifest "models/SHA256SUMS.$ALIAS"
# Point the engine at the model (first shard if split).
sed -i.bak -e "s|^MODEL_FILE=.*|MODEL_FILE=$FIRST|" -e "s|^MODEL_ALIAS=.*|MODEL_ALIAS=$ALIAS|" .env && rm -f .env.bak
echo "model ready: $FIRST ($ALIAS), verified"
