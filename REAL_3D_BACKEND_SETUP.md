# Real 3D Backend Setup

This app can now use a Dockerized Hunyuan3D-2 backend instead of only the built-in relief mesh pipeline.

## Current integration target

- Backend mode: `hunyuan_api`
- Expected API behavior: `POST /generate`
- Request body: base64 image
- Response body: binary `GLB`

## Recommended Docker-first stack

Use:

- app container
- Hunyuan3D API container
- local bind mounts / cache folders for model weights and output files

Main stack file:

- `compose.hunyuan-stack.yml`

## Start the stack

```powershell
docker compose -f compose.hunyuan-stack.yml up -d --build
```

## Main ports

- app: `http://127.0.0.1:8000`
- Hunyuan3D API: `http://127.0.0.1:8081`

## Default model settings

The Docker stack is currently configured for:

- `tencent/Hunyuan3D-2`
- subfolder: `hunyuan3d-dit-v2-0-turbo`
- shape generation only

This is a practical choice for RTX 4070 12GB.

## Why this path

- keeps the app service and the model service separate
- keeps almost all runtime logic inside Docker
- avoids baking huge model weights into the image
- preserves a clean path to the later `text -> image -> 3D asset` extension

## Persistent local folders

The compose file mounts:

- `./.hf-cache` for Hugging Face cache
- `./.u2net` for rembg cache
- `./outputs/hunyuan-cache` for generated backend files
- `./outputs` for app outputs

## Expected output when the real backend is connected

- `model.glb`
- `preview.png`
- `gray_render.png`
- `metadata.json`
- `asset_package.zip`

## Fallback behavior

If the external backend is unavailable and `FALLBACK_TO_RELIEF=true`, the app automatically falls back to the built-in OBJ relief pipeline.

## Notes for RTX 4070 12GB

- Hunyuan3D-2.0 shape-only is the most realistic target here
- Hunyuan3D-2.1 full texture pipeline is too heavy for this GPU
- if memory is tight, switch to a smaller model such as the `2mini` family by changing:
  - `HUNYUAN_MODEL_PATH`
  - `HUNYUAN_SUBFOLDER`

## Official references

- Tencent Hunyuan3D-2: https://github.com/Tencent-Hunyuan/Hunyuan3D-2
- Stability AI Stable Fast 3D: https://github.com/Stability-AI/stable-fast-3d
- Microsoft TRELLIS: https://github.com/microsoft/TRELLIS
