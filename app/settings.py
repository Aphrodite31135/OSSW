import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    model_backend: str = "relief"
    hunyuan3d_api_url: str = "http://host.docker.internal:8081/generate"
    hunyuan3d_timeout_seconds: int = 900
    text_to_image_backend: str = "none"
    text_to_image_api_url: str = "http://host.docker.internal:8090/generate"
    text_to_image_api_key: str | None = None
    text_to_image_timeout_seconds: int = 900
    cutout_backend_enabled: bool = False
    cutout_api_url: str = "http://host.docker.internal:8091/cutout"
    cutout_timeout_seconds: int = 900
    fallback_to_relief: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model_backend=os.getenv("MODEL_BACKEND", "relief").strip().lower(),
            hunyuan3d_api_url=os.getenv(
                "HUNYUAN3D_API_URL",
                "http://host.docker.internal:8081/generate",
            ).strip(),
            hunyuan3d_timeout_seconds=int(os.getenv("HUNYUAN3D_TIMEOUT_SECONDS", "900")),
            text_to_image_backend=os.getenv("TEXT_TO_IMAGE_BACKEND", "none").strip().lower(),
            text_to_image_api_url=os.getenv(
                "TEXT_TO_IMAGE_API_URL",
                "http://host.docker.internal:8090/generate",
            ).strip(),
            text_to_image_api_key=(os.getenv("TEXT_TO_IMAGE_API_KEY") or "").strip() or None,
            text_to_image_timeout_seconds=int(os.getenv("TEXT_TO_IMAGE_TIMEOUT_SECONDS", "900")),
            cutout_backend_enabled=os.getenv("CUTOUT_BACKEND_ENABLED", "false").strip().lower() == "true",
            cutout_api_url=os.getenv(
                "CUTOUT_API_URL",
                "http://host.docker.internal:8091/cutout",
            ).strip(),
            cutout_timeout_seconds=int(os.getenv("CUTOUT_TIMEOUT_SECONDS", "900")),
            fallback_to_relief=os.getenv("FALLBACK_TO_RELIEF", "true").strip().lower() != "false",
        )
