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
- `mesh.obj`
- `mesh.mtl`
- `asset_package.zip`

This keeps the pipeline lightweight for development while preserving a clean path to swap in a real image-to-3D model on the GPU runner later.

## Local run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Planned second release

The intended update release can extend this project to:

`text -> image -> 3D asset`

At that point you can add:

- a text-to-image generation stage
- a prompt input in the UI
- a selectable generation mode
- updated screenshots proving automatic redeployment
