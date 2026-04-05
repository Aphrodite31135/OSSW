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
- the app structure now supports an optional external real image-to-3D backend

## Confirmed Latest Successful Runs

As of the latest desktop verification:

- CI success run: `24006248037`
- CD success run: `24006258426`

Recent successful feature commits:

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

Current behavior:

- `MODEL_BACKEND=relief` uses the built-in mesh generator
- `MODEL_BACKEND=hunyuan_api` attempts to call an external backend
- if the real backend is unavailable and `FALLBACK_TO_RELIEF=true`, the app safely falls back to the built-in relief pipeline

This integration path has been tested for fallback behavior and works correctly.

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
- `requirements.txt`
- `Dockerfile`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy-blue-green.yml`
- `REAL_3D_BACKEND_SETUP.md`

## Recommended Next Steps

1. Test the currently deployed app with more real images
2. Decide whether the lightweight relief output is acceptable for the homework demo
3. If not acceptable, proceed to connect a real image-to-3D backend on the desktop GPU
4. Prefer Hunyuan3D-style or SF3D-style backend over TRELLIS for this environment
5. Once real image-to-3D is acceptable, start the second release:
   `text -> image -> 3D asset`

## What To Ask Codex Next

- Test the current deployed app and evaluate result quality
- Install and connect a real image-to-3D backend on the desktop GPU
- Refactor the app more aggressively if needed for better 3D quality
- Implement the later `text -> image -> 3D asset` extension
