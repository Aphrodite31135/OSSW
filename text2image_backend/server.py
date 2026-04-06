import argparse
import os
from io import BytesIO

import torch
import uvicorn
from diffusers import AutoPipelineForText2Image
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default=os.getenv("TEXT2IMAGE_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("TEXT2IMAGE_PORT", "8090")))
    parser.add_argument("--device", type=str, default=os.getenv("TEXT2IMAGE_DEVICE", "cuda"))
    parser.add_argument(
        "--model-id",
        type=str,
        default=os.getenv("TEXT2IMAGE_MODEL_ID", "playgroundai/playground-v2.5-1024px-aesthetic"),
    )
    parser.add_argument(
        "--num-inference-steps",
        type=int,
        default=int(os.getenv("TEXT2IMAGE_NUM_INFERENCE_STEPS", "24")),
    )
    parser.add_argument(
        "--guidance-scale",
        type=float,
        default=float(os.getenv("TEXT2IMAGE_GUIDANCE_SCALE", "3.0")),
    )
    parser.add_argument("--width", type=int, default=int(os.getenv("TEXT2IMAGE_WIDTH", "512")))
    parser.add_argument("--height", type=int, default=int(os.getenv("TEXT2IMAGE_HEIGHT", "512")))
    return parser.parse_args()


class TextToImageWorker:
    def __init__(self, model_id: str, device: str) -> None:
        self.device = device
        self.pipeline = AutoPipelineForText2Image.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        self.pipeline.set_progress_bar_config(disable=True)
        self.pipeline.to(device)

    @torch.inference_mode()
    def generate(
        self,
        prompt: str,
        negative_prompt: str,
        num_inference_steps: int,
        guidance_scale: float,
        width: int,
        height: int,
    ) -> bytes:
        generator = torch.Generator(device=self.device).manual_seed(1234)
        image = self.pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            generator=generator,
        ).images[0]

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        torch.cuda.empty_cache()
        return buffer.getvalue()


args = parse_args()
worker = TextToImageWorker(model_id=args.model_id, device=args.device)

app = FastAPI(title="Text to Image API Wrapper", version="1.0.0")
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
        "device": args.device,
        "model_id": args.model_id,
    }


@app.post("/generate")
async def generate(request: Request):
    params = await request.json()
    prompt = (params.get("prompt") or "").strip()
    negative_prompt = (params.get("negative_prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    try:
        image_bytes = worker.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=int(params.get("num_inference_steps", args.num_inference_steps)),
            guidance_scale=float(params.get("guidance_scale", args.guidance_scale)),
            width=int(params.get("width", args.width)),
            height=int(params.get("height", args.height)),
        )
        return Response(content=image_bytes, media_type="image/png")
    except torch.cuda.OutOfMemoryError as exc:
        torch.cuda.empty_cache()
        raise HTTPException(
            status_code=507,
            detail="GPU out of memory while running the text-to-image model.",
        ) from exc
    except Exception as exc:
        return JSONResponse(
            {
                "error": "generation_failed",
                "detail": str(exc),
            },
            status_code=500,
        )


if __name__ == "__main__":
    uvicorn.run(app, host=args.host, port=args.port)
