# Real 3D Backend Setup

This app can now use an external real image-to-3D backend instead of only the built-in relief mesh pipeline.

## Current integration target

- Backend mode: `hunyuan_api`
- Expected API behavior: `POST` one image and receive a binary `GLB` response

## Environment variables

```powershell
$env:MODEL_BACKEND = "hunyuan_api"
$env:HUNYUAN3D_API_URL = "http://host.docker.internal:8081/generate"
$env:FALLBACK_TO_RELIEF = "true"
```

## Why this path

- keeps the current FastAPI app simple
- works well with Docker Desktop because the app container can call the Windows host through `host.docker.internal`
- preserves a clean path to the later `text -> image -> 3D asset` extension

## Expected output when the real backend is connected

- `model.glb`
- `preview.png`
- `gray_render.png`
- `metadata.json`
- `asset_package.zip`

## Fallback behavior

If the external backend is unavailable and `FALLBACK_TO_RELIEF=true`, the app automatically falls back to the built-in OBJ relief pipeline.

## Official references

- Stability AI Stable Fast 3D: https://github.com/Stability-AI/stable-fast-3d
- Tencent Hunyuan3D-2: https://github.com/Tencent-Hunyuan/Hunyuan3D-2
- Microsoft TRELLIS: https://github.com/microsoft/TRELLIS
