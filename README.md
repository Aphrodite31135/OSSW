# Image to 3D Asset Studio

Homework-friendly baseline project for:

- FastAPI backend
- Simple web UI
- Docker containerization
- GitHub Actions CI
- Self-hosted runner deployment
- Blue-Green deployment story

## What this version does

The first release accepts one uploaded image and generates:

- `texture.png`
- `preview.png`
- `mesh.obj`
- `mesh.mtl`
- `metadata.json`
- `asset_package.zip`

The current release also includes:

- adjustable mesh detail
- adjustable height strength
- adjustable base thickness
- a solid relief-style mesh with side walls
- a lightweight metadata file for demo/report screenshots

This keeps the pipeline lightweight for development while preserving a clean path to swap in a real image-to-3D model on the GPU runner later.

## Local run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Real image-to-3D backend

The app now supports an optional external real 3D backend.

Recommended mode:

- built-in app in Docker
- Hunyuan3D API backend in Docker
- model caches stored in local mounted folders

Main stack file:

- `compose.hunyuan-stack.yml`

Main environment variables:

- `MODEL_BACKEND=relief` for the built-in lightweight mesh pipeline
- `MODEL_BACKEND=hunyuan_api` to call an external Hunyuan3D-style API server
- `HUNYUAN3D_API_URL=http://hunyuan3d-api:8081/generate`
- `FALLBACK_TO_RELIEF=true` to fall back to the built-in mesh when the external backend is unavailable

When the real backend is enabled, the app packages:

- `model.glb`
- `preview.png`
- `gray_render.png`
- `metadata.json`
- `asset_package.zip`

This keeps the current homework demo stable while providing a realistic path toward a true single-image 3D generation backend on the desktop GPU.

## Planned second release

The intended update release can extend this project to:

`text -> image -> 3D asset`

At that point you can add:

- a text-to-image generation stage
- a prompt input in the UI
- a selectable generation mode
- updated screenshots proving automatic redeployment
