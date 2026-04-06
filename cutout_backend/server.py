import io
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image, ImageFilter
from rembg import new_session, remove


MODEL_NAME = os.getenv("CUTOUT_MODEL", "u2net")
SESSION = new_session(MODEL_NAME)


def soften_alpha_edges(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    alpha = alpha.filter(ImageFilter.MaxFilter(size=5))
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=1.2))
    rgba.putalpha(alpha)
    return rgba

app = FastAPI(title="OSSW Cutout API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "model": MODEL_NAME,
    }


@app.post("/cutout")
async def cutout(request: Request) -> Response:
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Request body must contain image bytes.")

    try:
        image = Image.open(io.BytesIO(body))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not parse input image.") from exc

    try:
        isolated = remove(
            image,
            session=SESSION,
            alpha_matting=False,
            post_process_mask=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Background removal failed: {exc}") from exc

    if isinstance(isolated, bytes):
        isolated_image = Image.open(io.BytesIO(isolated)).convert("RGBA")
    else:
        isolated_image = isolated.convert("RGBA") if isolated.mode != "RGBA" else isolated

    isolated_image = soften_alpha_edges(isolated_image)
    buffer = io.BytesIO()
    isolated_image.save(buffer, format="PNG")
    output = buffer.getvalue()

    return Response(content=output, media_type="image/png")
