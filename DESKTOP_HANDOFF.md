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
- the app container has been restarted locally with:
  - `MODEL_BACKEND=hunyuan_api`
  - `HUNYUAN3D_API_URL=http://host.docker.internal:8081/generate`
  - `HUNYUAN3D_TIMEOUT_SECONDS=1800`
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
- `app/templates/index.html`
- `app/static/app.js`
- `app/static/styles.css`
- `compose.hunyuan-stack.yml`
- `hunyuan_backend/Dockerfile`
- `hunyuan_backend/entrypoint.sh`
- `hunyuan_backend/server.py`
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

1. Test the Hunyuan-connected local app at `127.0.0.1:8000` with more real images
2. Evaluate whether Hunyuan output quality is good enough for the homework demo
3. Commit and push the current local Hunyuan-related changes if they are accepted
4. Re-run CI/CD so future live containers also boot with the Hunyuan environment variables
5. Once real image-to-3D is acceptable, start the second release:
   `text -> image -> 3D asset`

## What To Ask Codex Next

- Test the current deployed app and evaluate result quality
- Install and connect a real image-to-3D backend on the desktop GPU
- Refactor the app more aggressively if needed for better 3D quality
- Implement the later `text -> image -> 3D asset` extension
