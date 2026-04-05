import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    model_backend: str = "relief"
    hunyuan3d_api_url: str = "http://host.docker.internal:8081/generate"
    hunyuan3d_timeout_seconds: int = 900
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
            fallback_to_relief=os.getenv("FALLBACK_TO_RELIEF", "true").strip().lower() != "false",
        )
