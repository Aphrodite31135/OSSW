from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.schemas import AssetResponse, HealthResponse
from app.services.asset_pipeline import AssetPipeline
from app.services.real3d_client import Real3DClientError
from app.settings import Settings


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
OUTPUT_DIR = BASE_DIR / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings = Settings.from_env()

app = FastAPI(
    title="Image to 3D Asset Studio",
    description="Upload a reference image and generate a simple 3D asset package.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
pipeline = AssetPipeline(output_dir=OUTPUT_DIR, settings=settings)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": "Image to 3D Asset Studio",
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/generate-asset", response_model=AssetResponse)
async def generate_asset(
    image: UploadFile = File(...),
    resolution: int = Form(96),
    height_scale: float = Form(0.32),
    base_thickness: float = Form(0.14),
) -> AssetResponse:
    content_type = image.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")

    if resolution not in {64, 96, 128}:
        raise HTTPException(status_code=400, detail="Resolution must be 64, 96, or 128.")
    if not 0.08 <= height_scale <= 0.7:
        raise HTTPException(status_code=400, detail="Height strength must be between 0.08 and 0.7.")
    if not 0.04 <= base_thickness <= 0.3:
        raise HTTPException(status_code=400, detail="Base thickness must be between 0.04 and 0.3.")

    try:
        result = pipeline.generate(
            image_bytes=image_bytes,
            original_name=image.filename or "upload.png",
            resolution=resolution,
            height_scale=height_scale,
            base_thickness=base_thickness,
        )
    except Real3DClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AssetResponse(**result)
