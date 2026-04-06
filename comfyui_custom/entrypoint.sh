#!/bin/bash
set -euo pipefail

checkpoint_dir="${CHECKPOINT_DIR:-/opt/ComfyUI/models/checkpoints}"
checkpoint_name="${COMFYUI_CHECKPOINT_NAME:-SSD-1B-A1111.safetensors}"
checkpoint_url="${COMFYUI_CHECKPOINT_URL:-}"
checkpoint_path="${checkpoint_dir}/${checkpoint_name}"

mkdir -p "${checkpoint_dir}"

if [ ! -f "${checkpoint_path}" ]; then
  if [ -z "${checkpoint_url}" ]; then
    echo "COMFYUI_CHECKPOINT_URL is required when the checkpoint is missing." >&2
    exit 1
  fi

  echo "Downloading ${checkpoint_name} from ${checkpoint_url}"
  python - "${checkpoint_url}" "${checkpoint_path}" <<'PY'
import os
import sys
import urllib.request

url = sys.argv[1]
dest = sys.argv[2]
tmp = dest + ".part"
os.makedirs(os.path.dirname(dest), exist_ok=True)
urllib.request.urlretrieve(url, tmp)
os.replace(tmp, dest)
print(f"Saved checkpoint to {dest}")
PY
else
  echo "Using existing checkpoint at ${checkpoint_path}"
fi

cd /opt/ComfyUI
exec ./comfyui-api
