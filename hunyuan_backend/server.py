import argparse
import base64
import os
import tempfile
from io import BytesIO

import torch
import trimesh
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

from hy3dgen.rembg import BackgroundRemover
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline


SAVE_DIR = os.getenv("HUNYUAN_SAVE_DIR", "/workspace/cache")
os.makedirs(SAVE_DIR, exist_ok=True)


def load_image_from_base64(image: str) -> Image.Image:
    return Image.open(BytesIO(base64.b64decode(image))).convert("RGB")


class ModelWorker:
    def __init__(
        self,
        model_path: str,
        subfolder: str,
        device: str,
    ) -> None:
        self.model_path = model_path
        self.subfolder = subfolder
        self.device = device
        self.rembg = BackgroundRemover()
        self.pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
            model_path,
            subfolder=subfolder,
            use_safetensors=True,
            device=device,
        )
        self.pipeline.enable_flashvdm(mc_algo="mc")

    @torch.inference_mode()
    def generate_glb(
        self,
        image_b64: str,
        seed: int,
        octree_resolution: int,
        num_inference_steps: int,
        guidance_scale: float,
    ) -> str:
        image = load_image_from_base64(image_b64)
        image = self.rembg(image)
        generator = torch.Generator(self.device).manual_seed(seed)

        mesh = self.pipeline(
            image=image,
            generator=generator,
            octree_resolution=octree_resolution,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            mc_algo="mc",
        )[0]

        with tempfile.NamedTemporaryFile(suffix=".glb", delete=False, dir=SAVE_DIR) as temp_file:
            mesh.export(temp_file.name)
            save_path = temp_file.name

        torch.cuda.empty_cache()
        return save_path


app = FastAPI(title="Hunyuan3D API Wrapper", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

worker: ModelWorker | None = None


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "device": args.device,
        "model_path": args.model_path,
        "subfolder": args.subfolder,
    }


@app.post("/generate")
async def generate(request: Request):
    if worker is None:
        raise HTTPException(status_code=503, detail="Hunyuan3D model is not ready.")

    params = await request.json()
    image_b64 = params.get("image")
    if not image_b64:
        raise HTTPException(status_code=400, detail="Request must include a base64 encoded image.")

    seed = int(params.get("seed", args.seed))
    octree_resolution = int(params.get("octree_resolution", args.octree_resolution))
    num_inference_steps = int(params.get("num_inference_steps", args.num_inference_steps))
    guidance_scale = float(params.get("guidance_scale", args.guidance_scale))

    try:
        file_path = worker.generate_glb(
            image_b64=image_b64,
            seed=seed,
            octree_resolution=octree_resolution,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )
        return FileResponse(file_path, media_type="model/gltf-binary", filename="model.glb")
    except torch.cuda.OutOfMemoryError as exc:
        torch.cuda.empty_cache()
        raise HTTPException(
            status_code=507,
            detail=(
                "GPU out of memory while running Hunyuan3D. "
                "Try a smaller model or lower octree resolution."
            ),
        ) from exc
    except Exception as exc:
        return JSONResponse(
            {
                "error": "generation_failed",
                "detail": str(exc),
            },
            status_code=500,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default=os.getenv("HUNYUAN_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("HUNYUAN_PORT", "8081")))
    parser.add_argument("--device", type=str, default=os.getenv("HUNYUAN_DEVICE", "cuda"))
    parser.add_argument("--model-path", type=str, default=os.getenv("HUNYUAN_MODEL_PATH", "tencent/Hunyuan3D-2"))
    parser.add_argument(
        "--subfolder",
        type=str,
        default=os.getenv("HUNYUAN_SUBFOLDER", "hunyuan3d-dit-v2-0-turbo"),
    )
    parser.add_argument("--seed", type=int, default=int(os.getenv("HUNYUAN_SEED", "1234")))
    parser.add_argument(
        "--octree-resolution",
        type=int,
        default=int(os.getenv("HUNYUAN_OCTREE_RESOLUTION", "192")),
    )
    parser.add_argument(
        "--num-inference-steps",
        type=int,
        default=int(os.getenv("HUNYUAN_NUM_INFERENCE_STEPS", "30")),
    )
    parser.add_argument(
        "--guidance-scale",
        type=float,
        default=float(os.getenv("HUNYUAN_GUIDANCE_SCALE", "5.5")),
    )
    return parser.parse_args()


args = parse_args()
worker = ModelWorker(
    model_path=args.model_path,
    subfolder=args.subfolder,
    device=args.device,
)

