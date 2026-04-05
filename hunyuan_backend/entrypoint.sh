#!/usr/bin/env bash
set -euo pipefail

cd /opt/Hunyuan3D-2
python /workspace/server.py \
  --host "${HUNYUAN_HOST:-0.0.0.0}" \
  --port "${HUNYUAN_PORT:-8081}" \
  --device "${HUNYUAN_DEVICE:-cuda}" \
  --model-path "${HUNYUAN_MODEL_PATH:-tencent/Hunyuan3D-2}" \
  --subfolder "${HUNYUAN_SUBFOLDER:-hunyuan3d-dit-v2-0-turbo}" \
  --seed "${HUNYUAN_SEED:-1234}" \
  --octree-resolution "${HUNYUAN_OCTREE_RESOLUTION:-192}" \
  --num-inference-steps "${HUNYUAN_NUM_INFERENCE_STEPS:-30}" \
  --guidance-scale "${HUNYUAN_GUIDANCE_SCALE:-5.5}"

