# Desktop Handoff

## Project Goal

The homework goal is:

`AI app development -> Docker image build -> GitHub Actions CI -> Docker Hub push -> Self-hosted Runner CD -> Blue-Green redeploy -> feature update and automatic service refresh`

## Planned Service Scope

1. First release: `image -> 3D asset`
2. Second release: `text -> image -> 3D asset`
3. Include a user-facing Web UI
4. Include Blue-Green style redeployment in the deployment story

## Current Progress

- GitHub repository is ready:
  `https://github.com/Aphrodite31135/OSSW`
- GitHub Actions secrets have been created:
  - `DOCKERHUB_USERNAME`
  - `DOCKERHUB_TOKEN`
- Baseline homework code has been created:
  - FastAPI backend
  - Image upload Web UI
  - Lightweight 3D asset package demo generator
  - `Dockerfile`
  - `ci.yml`
  - `deploy-blue-green.yml`
- Project files have been uploaded to GitHub

## Important Project Files

- `app/main.py`
- `app/schemas.py`
- `app/services/asset_pipeline.py`
- `app/templates/index.html`
- `app/static/app.js`
- `app/static/styles.css`
- `requirements.txt`
- `Dockerfile`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy-blue-green.yml`

## Current Blocking Issue

GitHub Actions CI is failing.

Error message:

`Error response from daemon: unauthorized: incorrect username or password`

Meaning:

- Docker Hub login failed inside GitHub Actions
- The likely cause is incorrect `DOCKERHUB_USERNAME` or `DOCKERHUB_TOKEN`

Required fix:

1. Recheck Docker Hub username
2. Reissue a Docker Hub access token if needed
3. Update GitHub Actions secrets
4. Re-run the CI workflow

## Deployment Notes

- The self-hosted runner will be set up on the desktop with the RTX 4070
- Docker deployment, GPU inference, and final verification should be done on that desktop
- The current `deploy-blue-green.yml` is a homework-friendly Blue-Green scaffold and should be tested again on the desktop environment

## Next Steps

1. Clone the `OSSW` repository on the desktop
2. Check Git, Docker, Python, and NVIDIA/GPU environment
3. Fix the Docker Hub authentication issue
4. Confirm CI success
5. Register the desktop as a self-hosted runner
6. Verify first deployment success
7. Extend the project to `text -> image -> 3D asset`

## What To Ask Codex Next

- Verify the desktop environment setup
- Fix Docker Hub authentication in GitHub Actions
- Help configure the self-hosted runner
- Connect a real image-to-3D model on the desktop GPU
- Implement the later `text-to-image` extension
