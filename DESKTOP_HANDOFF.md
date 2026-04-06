# Desktop Handoff

## Project Goal

The homework goal is:

`AI app development -> Docker image build -> GitHub Actions CI -> Docker Hub push -> Self-hosted Runner CD -> Blue-Green redeploy -> feature update and automatic service refresh`

## Planned Service Scope

1. First release: `image -> 3D asset`
2. Second release: `text -> image -> 3D asset`
3. Include a user-facing Web UI
4. Include Blue-Green style redeployment in the deployment story

## Current Status Summary

The desktop environment is now fully usable for the homework workflow.

- Docker Hub authentication issue has been fixed
- GitHub Actions CI is working
- self-hosted runner is installed on the desktop
- Blue-Green deployment is working on the desktop
- the `image -> 3D asset` first release has been upgraded
- the app now also outputs a grayscale shaded render image
- the app structure now supports an external real image-to-3D backend
- a Dockerized Hunyuan3D backend has been added and successfully tested with real inference
- the local live app on `127.0.0.1:8000` is now configured to use the Hunyuan3D backend
- a first `text -> image -> 3D asset` path has also been connected locally
- the text-to-image backend has now been switched to `playgroundai/playground-v2.5-1024px-aesthetic`
- the new text backend and the full `text -> image -> 3D` path have both been re-tested successfully on this desktop
- an optional stronger Docker Hub-based `SD 3.5 Large Turbo` stack has now been wired into the repo for later testing with a Hugging Face token
- an optional token-free ComfyUI stack has now also been wired into the repo for later testing with public checkpoints
- the token-free ComfyUI path has now been upgraded into a custom image with a custom workflow and has been validated end-to-end on the live desktop app

## Confirmed Latest Successful Runs

As of the latest desktop verification:

- CI success run: `24006248037`
- CD success run: `24006258426`

Recent successful feature commits:

- `d252b37` `Add Dockerized Hunyuan3D backend stack`
- `791bfea` `Add real image-to-3d backend integration`
- `0f59116` `Add gray shaded render to asset output`
- `ac1e827` `Upgrade image-to-3d first release`
- `b1e030a` `Make blue-green cleanup idempotent`
- `26d5685` `Fix Windows shell for self-hosted deploy`

## Current Deployment State

The desktop is now acting as the deployment server.

- repository: `https://github.com/Aphrodite31135/OSSW`
- self-hosted runner name: `OSSW-desktop-runner`
- stable app port: `8000`
- Blue-Green slot ports:
  - Blue: `8001`
  - Green: `8002`
- health endpoint:
  - `http://127.0.0.1:8000/health`

Current local runtime state on this desktop:

- `image3d-live` is running on port `8000`
- `hunyuan3d-api` is running on port `8081`
- `text2image-api` is running on port `8090`
- the app container has been restarted locally with:
  - `MODEL_BACKEND=hunyuan_api`
  - `HUNYUAN3D_API_URL=http://host.docker.internal:8081/generate`
  - `HUNYUAN3D_TIMEOUT_SECONDS=1800`
  - `TEXT_TO_IMAGE_BACKEND=flux_api`
  - `TEXT_TO_IMAGE_API_URL=http://host.docker.internal:8090/generate`
  - `TEXT_TO_IMAGE_TIMEOUT_SECONDS=1800`
  - `FALLBACK_TO_RELIEF=true`
- Blue-Green secondary slot containers were intentionally cleaned up, so only the stable app container remains active for now

## What Was Fixed On This Desktop

### 1. Docker Hub authentication

The original blocker was:

`Error response from daemon: unauthorized: incorrect username or password`

This was fixed by:

- issuing a new Docker Hub access token
- updating GitHub repository secrets:
  - `DOCKERHUB_USERNAME`
  - `DOCKERHUB_TOKEN`
- re-running the CI workflow

### 2. Self-hosted runner setup

The desktop runner was installed and registered successfully.

- runner folder: local `actions-runner/` directory on the desktop repo
- runner status: online and working

### 3. PowerShell workflow issues

Two Windows-specific deployment issues were fixed:

- PowerShell execution policy was blocking workflow scripts
- `deploy-blue-green.yml` used `pwsh`, but the desktop runner only had Windows PowerShell available

These were fixed by:

- setting execution policy for the current user
- changing workflow shell steps from `pwsh` to `powershell`

### 4. Blue-Green deployment reliability

The deployment workflow originally failed when a container to delete did not already exist.

This was fixed by making container cleanup idempotent in:

- `.github/workflows/deploy-blue-green.yml`

## Current App Behavior

The current first release is still homework-friendly and lightweight, but it is no longer just the original baseline.

### Built-in default pipeline

The default path is still a lightweight relief-style mesh generator.

It currently generates:

- `mesh.obj`
- `mesh.mtl`
- `texture.png`
- `preview.png`
- `gray_render.png`
- `metadata.json`
- `asset_package.zip`

### UI/feature upgrades already completed

- image upload UI
- adjustable mesh detail
- adjustable height strength
- adjustable base thickness
- color preview image
- grayscale shaded render image
- downloadable ZIP package

## Important Technical Limitation

The current built-in pipeline is **not** a true image-to-3D reconstruction model.

It is a relief / height-map style mesh generator. This means:

- good fit for logos, icons, signs, embossed shapes
- poor fit for complex real-world photos such as buildings
- single-image building photos can produce spiky or slab-like OBJ output rather than a realistic 3D building

This is not simply a bug; it is a limitation of the current lightweight algorithm.

## Real Image-to-3D Integration Progress

The app structure has now been refactored so that it can call an external real image-to-3D backend.

New files added for this:

- `app/settings.py`
- `app/services/real3d_client.py`
- `REAL_3D_BACKEND_SETUP.md`
- `compose.hunyuan-stack.yml`
- `hunyuan_backend/Dockerfile`
- `hunyuan_backend/entrypoint.sh`
- `hunyuan_backend/server.py`

Current behavior:

- `MODEL_BACKEND=relief` uses the built-in mesh generator
- `MODEL_BACKEND=hunyuan_api` attempts to call an external backend
- if the real backend is unavailable and `FALLBACK_TO_RELIEF=true`, the app safely falls back to the built-in relief pipeline

This integration path has now been tested in two ways:

- fallback behavior works correctly when the real backend is unavailable
- real Hunyuan3D inference works correctly when the backend is running

Verified real inference result on this desktop:

- backend server health:
  - `http://127.0.0.1:8081/health`
- direct Hunyuan API generation:
  - input image was sent to `/generate`
  - GLB output was successfully returned
  - sample generated file:
    - `outputs/real3d_test/model.glb`
- app-level generation through `http://127.0.0.1:8000/api/generate-asset` returned:
  - `backend: "hunyuan_api"`
  - `asset_format: "zip+glb"`

Important implementation note:

- the initial Hunyuan wrapper container loaded the model and then exited because `uvicorn.run(...)` was missing in `hunyuan_backend/server.py`
- this has now been fixed
- OpenGL runtime support was also improved in the Hunyuan backend image by adding `libopengl0`
- the compose healthcheck start period was extended because first model load is slow

Current limitation:

- the live desktop app is already pointing to Hunyuan3D locally
- the GitHub Actions Blue-Green deployment workflow has now also been updated so new production containers receive the Hunyuan environment variables automatically

## Text-to-Image to 3D Progress

The second-release path has now been prototyped locally:

- `text -> image -> 3D asset`

New files added for this:

- `app/services/text2image_client.py`
- `text2image_backend/Dockerfile`
- `text2image_backend/server.py`

Current local behavior:

- the Web UI now supports both:
  - `image -> 3D`
  - `text -> image -> 3D`
- text mode sends a prompt to a local text-to-image API container
- the generated image is then passed to the Hunyuan3D backend
- the final app response returns:
  - `source_mode`
  - `source_image_url`
  - `asset_format: "zip+glb"`

What has already been verified:

- the local text-to-image API runs on:
  - `http://127.0.0.1:8090/health`
- direct text-to-image generation returned PNG outputs successfully
- app-level `text -> image -> 3D` calls returned successful `zip+glb` responses after the backend became healthy
- after switching models, `http://127.0.0.1:8090/health` now reports:
  - `model_id: "playgroundai/playground-v2.5-1024px-aesthetic"`
- a full app-level retest also succeeded after the model switch:
  - sample successful job id:
    - `7f7f773aa8dc`
  - returned fields included:
    - `backend: "hunyuan_api"`
    - `source_mode: "text"`
    - `asset_format: "zip+glb"`

Important quality limitation discovered:

- the initial local text-to-image backend used `stabilityai/sdxl-turbo`
- even with prompt strengthening, negative prompts, padding, and object recentering, it still often generates building images that are too scene-like, too cropped, or too close-up
- this causes Hunyuan3D to reconstruct poor box-like or slab-like geometry

Current decision:

- the user explicitly approved replacing the current text-to-image model if necessary
- an attempted switch to `FLUX.1-schnell` failed locally because the Hugging Face repo is gated and requires authentication
- `stabilityai/stable-diffusion-xl-base-1.0` works as a public replacement, but the user wants a stronger model
- an attempted switch to `stabilityai/stable-diffusion-3.5-medium` also failed locally because the model requires gated access
- the current selected public replacement is now `playgroundai/playground-v2.5-1024px-aesthetic`
- this model now boots successfully in Docker on the desktop GPU and is currently the most realistic public step up from SDXL Base that has actually worked in this environment
- for a higher-end but gated option, the repo now also includes `compose.sd35-dockerhub-stack.yml`, which targets `stabilityai/stable-diffusion-3.5-large-turbo` through the Docker Hub image `blumfontein/docker-stable-diffusion`
- that path still requires `HUGGING_FACE_HUB_TOKEN` access and has not been fully runtime-tested on this desktop yet
- for a token-free workflow-driven option, the repo now also includes `compose.comfyui-stack.yml`, which now builds a custom ComfyUI image
- that custom image uses a public checkpoint volume at `.comfy-models/` and downloads `segmind/SSD-1B` as `SSD-1B-A1111.safetensors`
- the app-facing route for this stack is now `POST /workflow/object_txt2img`
- that path is intended to improve object framing control more than raw model quality
- this custom ComfyUI path has now been tested successfully with:
  - backend health on `http://127.0.0.1:8090/health`
  - live app text-to-image-to-3D success job:
    - `76b1bc7db39a`
  - custom workflow test output:
    - `outputs/comfyui_custom_test/source_input.png`
- key new files for this path:
  - `comfyui_custom/Dockerfile`
  - `comfyui_custom/entrypoint.sh`
  - `comfyui_custom/object_txt2img.ts`
  - `comfyui_custom/warmup.json`

## Model Direction Chosen So Far

The user asked whether the model could be changed, and the answer is yes.

After reviewing model options, the current direction is:

- keep the app stable now
- test current results first
- if results are not good enough, replace more of the source code from the ground up if needed
- prefer a real image-to-3D backend over trying to force the lightweight relief pipeline to solve everything

The user explicitly said they are okay with:

- changing the model later
- heavily refactoring the codebase if that leads to better optimization or better 3D output

## Candidate Real 3D Backends Reviewed

These official repos were reviewed as references:

- Stability AI Stable Fast 3D:
  `https://github.com/Stability-AI/stable-fast-3d`
- Tencent Hunyuan3D-2:
  `https://github.com/Tencent-Hunyuan/Hunyuan3D-2`
- Microsoft TRELLIS:
  `https://github.com/microsoft/TRELLIS`

Important conclusion:

- TRELLIS does not currently provide a clear official quantized deployment path suitable for this homework desktop flow
- TRELLIS also remains heavier in GPU and Linux assumptions
- the current app integration path was written with a Hunyuan-style external API in mind because it is easier to wire into the existing Docker/Desktop workflow

## Report / Screenshot Materials Already Prepared Locally

These local files were created for report preparation but are not committed:

- `SCREENSHOT_CHECKLIST.md`
- `REPORT_DRAFT.md`
- `report_assets/`

The `report_assets/` folder contains:

- input/output comparison images
- wireframe visualization images
- grayscale mesh visualization images
- generated ZIP packages used for screenshots

## Important Project Files

- `app/main.py`
- `app/schemas.py`
- `app/settings.py`
- `app/services/asset_pipeline.py`
- `app/services/real3d_client.py`
- `app/services/text2image_client.py`
- `app/templates/index.html`
- `app/static/app.js`
- `app/static/styles.css`
- `compose.hunyuan-stack.yml`
- `hunyuan_backend/Dockerfile`
- `hunyuan_backend/entrypoint.sh`
- `hunyuan_backend/server.py`
- `text2image_backend/Dockerfile`
- `text2image_backend/server.py`
- `requirements.txt`
- `Dockerfile`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy-blue-green.yml`
- `REAL_3D_BACKEND_SETUP.md`

## Local Report-Only Files

There are local report-only files that remain untracked and should not be committed unless intentionally needed:

- `REPORT_DRAFT.md`
- `SCREENSHOT_CHECKLIST.md`
- `report_assets/`

## Recommended Next Steps

1. Compare `Playground v2.5` source-image framing against the previous SDXL-based outputs with the same prompts
2. Tighten the default building/object prompt template further if framing is still too close
3. Commit and push the current text-to-image-to-3D changes once quality is acceptable
4. Re-run CI/CD so future live containers also boot with both the Hunyuan and text-to-image environment variables
5. If quality is still insufficient, test another non-gated public text-to-image model rather than returning to SDXL Base
6. If a Hugging Face token is available, test `compose.sd35-dockerhub-stack.yml` and compare SD 3.5 Large Turbo framing against Playground v2.5
7. Test `compose.comfyui-stack.yml` and compare whether ComfyUI workflow control helps keep full objects in frame more reliably

## What To Ask Codex Next

- Test the current deployed app and evaluate result quality
- Install and connect a real image-to-3D backend on the desktop GPU
- Refactor the app more aggressively if needed for better 3D quality
- Implement the later `text -> image -> 3D asset` extension
