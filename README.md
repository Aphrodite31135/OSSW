# Image to 3D Asset Studio

Homework-friendly baseline project for:

- FastAPI backend
- Simple web UI
- Docker containerization
- GitHub Actions CI
- Self-hosted runner deployment
- Blue-Green deployment story

## What this version does

The current app supports:

- `image -> 3D asset`
- `text -> image -> 3D asset`

The image-based path generates:

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

## Text-to-image backend

The app can also generate a source image from text before sending it to the 3D backend.

Main environment variables:

- `TEXT_TO_IMAGE_BACKEND=flux_api`
- `TEXT_TO_IMAGE_API_URL=http://text2image-api:8090/generate`
- `TEXT2IMAGE_MODEL_ID=playgroundai/playground-v2.5-1024px-aesthetic`

Recommended local stack:

- app in Docker
- text-to-image backend in Docker
- Hunyuan3D backend in Docker

The combined stack is described in:

- `compose.hunyuan-stack.yml`

Current desktop-tested text model:

- `playgroundai/playground-v2.5-1024px-aesthetic`
- chosen because it is a stronger public option than the earlier SDXL-based backend without requiring gated Hugging Face access

## Optional token-free ComfyUI path

The repo now also includes an optional ComfyUI-based text backend:

- stack file: `compose.comfyui-stack.yml`
- app mode: `TEXT_TO_IMAGE_BACKEND=comfyui_api`
- API target: `POST /workflow/object_txt2img`
- Docker image: custom build from `saladtechnologies/comfyui:comfy0.3.61-api1.9.2-torch2.8.0-cuda12.8-dreamshaper8`

This path is designed for:

- token-free operation with public checkpoints
- easier workflow control for centered object framing
- future extension with extra ComfyUI nodes and custom workflows

Current default ComfyUI workflow behavior:

- downloads `segmind/SSD-1B` as `SSD-1B-A1111.safetensors` into `.comfy-models/`
- sends requests to a custom ComfyUI workflow route
- receives a base64 image response
- forwards the generated image to Hunyuan3D

Important note:

- this ComfyUI path is primarily for workflow control and token-free operation
- the currently running public Playground path may still produce stronger raw aesthetics in some cases
- ComfyUI becomes most useful when we start adding framing, background cleanup, and category-specific generation workflows

## Optional stronger Docker Hub backend

If you want a higher-end text-to-image backend than the current public Playground setup, the repo now also includes an optional Docker Hub stack for:

- `stabilityai/stable-diffusion-3.5-large-turbo`
- Docker Hub image: `blumfontein/docker-stable-diffusion`

Stack file:

- `compose.sd35-dockerhub-stack.yml`

Important notes:

- this path needs a Hugging Face token with access to the gated Stability model
- set `HUGGING_FACE_HUB_TOKEN` before starting the stack
- the app uses `TEXT_TO_IMAGE_BACKEND=openai_image_api` for this stack because the Docker Hub service exposes an OpenAI-compatible image endpoint
- this model is stronger than the current public Playground path, but it is heavier and may be tight on a 12GB GPU depending on prompt and resolution

## Planned next release

The next step after this release is to improve:

- prompt quality and image style control
- text-to-image backend quality and speed
- production redeploy flow for the added text-to-image backend
