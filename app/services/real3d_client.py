import base64
import json
from urllib import error, request


class Real3DClientError(RuntimeError):
    pass


class Hunyuan3DClient:
    def __init__(self, api_url: str, timeout_seconds: int = 900) -> None:
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds

    def generate_glb(self, image_bytes: bytes) -> bytes:
        payload = json.dumps(
            {
                "image": base64.b64encode(image_bytes).decode("ascii"),
            }
        ).encode("utf-8")
        req = request.Request(
            self.api_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise Real3DClientError(f"Hunyuan3D API returned HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise Real3DClientError(f"Could not reach Hunyuan3D API at {self.api_url}.") from exc

        if "application/json" in content_type:
            detail = body.decode("utf-8", errors="replace")
            raise Real3DClientError(f"Hunyuan3D API returned JSON instead of a GLB file: {detail}")

        if not body:
            raise Real3DClientError("Hunyuan3D API returned an empty response.")

        return body
