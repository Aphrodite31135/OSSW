import http.client
import base64
import json
import time
from urllib import error, request


class TextToImageClientError(RuntimeError):
    pass


DEFAULT_PROMPT_PREFIX = (
    "single isolated object, centered composition, full object visible, "
    "object completely inside the frame with wide margins, small object in frame, "
    "clean studio product render, plain light background, no cropped edges, no close-up framing, "
    "entire silhouette visible from top to bottom, floating cutout object, no base platform, no landscaping"
)

DEFAULT_NEGATIVE_PROMPT = (
    "cropped, close-up, zoomed in, cut off, partial object, multiple objects, "
    "busy background, city scene, street scene, room interior, landscape, human, text, watermark, "
    "trees, plants, podium, pedestal, platform, landscaping, grass, bushes, ground plane"
)

class TextToImageClient:
    def __init__(self, api_url: str, timeout_seconds: int = 900, api_key: str | None = None) -> None:
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key

    def generate_image(self, prompt: str, backend: str) -> bytes:
        composed_prompt = f"{prompt.strip()}, {DEFAULT_PROMPT_PREFIX}"
        if backend == "openai_image_api":
            payload = json.dumps(
                {
                    "prompt": composed_prompt,
                    "size": "1024x1024",
                    "quality": "high",
                    "response_format": "b64_json",
                }
            ).encode("utf-8")
        elif backend == "comfyui_api":
            payload = json.dumps(
                {
                    "input": {
                        "prompt": composed_prompt,
                        "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
                        "width": 1024,
                        "height": 1024,
                        "steps": 20,
                        "cfg_scale": 9.0,
                    }
                }
            ).encode("utf-8")
        else:
            payload = json.dumps(
                {
                    "prompt": composed_prompt,
                    "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
                }
            ).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = request.Request(
            self.api_url,
            data=payload,
            headers=headers,
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(4):
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    body = response.read()
                    content_type = response.headers.get("Content-Type", "")
                break
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise TextToImageClientError(f"Text-to-image API returned HTTP {exc.code}: {detail}") from exc
            except (error.URLError, http.client.RemoteDisconnected) as exc:
                last_error = exc
                if attempt == 3:
                    raise TextToImageClientError(
                        f"Could not reach text-to-image API at {self.api_url}."
                    ) from exc
                time.sleep(3)
        else:
            raise TextToImageClientError(f"Could not reach text-to-image API at {self.api_url}.") from last_error

        if "application/json" in content_type:
            if backend == "comfyui_api":
                return self._decode_comfyui_response(body)
            if backend != "openai_image_api":
                detail = body.decode("utf-8", errors="replace")
                raise TextToImageClientError(f"Text-to-image API returned JSON instead of an image: {detail}")
            return self._decode_openai_image_response(body)

        if not body:
            raise TextToImageClientError("Text-to-image API returned an empty response.")

        return body

    def _decode_openai_image_response(self, body: bytes) -> bytes:
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise TextToImageClientError("Text-to-image API returned invalid JSON.") from exc

        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise TextToImageClientError(f"Text-to-image API returned unexpected JSON: {payload}")

        first = data[0]
        if not isinstance(first, dict):
            raise TextToImageClientError(f"Text-to-image API returned unexpected JSON: {payload}")

        b64_json = first.get("b64_json")
        if isinstance(b64_json, str) and b64_json:
            try:
                return base64.b64decode(b64_json)
            except Exception as exc:  # pragma: no cover - defensive decode path
                raise TextToImageClientError("Could not decode base64 image response.") from exc

        image_url = first.get("url")
        if isinstance(image_url, str) and image_url:
            try:
                with request.urlopen(image_url, timeout=self.timeout_seconds) as response:
                    return response.read()
            except Exception as exc:  # pragma: no cover - defensive fallback path
                raise TextToImageClientError(f"Could not download generated image from {image_url}.") from exc

        raise TextToImageClientError(f"Text-to-image API returned JSON without image data: {payload}")

    def _decode_comfyui_response(self, body: bytes) -> bytes:
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise TextToImageClientError("ComfyUI API returned invalid JSON.") from exc

        images = payload.get("images")
        if not isinstance(images, list) or not images:
            raise TextToImageClientError(f"ComfyUI API returned no images: {payload}")

        first = images[0]
        if not isinstance(first, str) or not first:
            raise TextToImageClientError(f"ComfyUI API returned invalid image data: {payload}")

        try:
            return base64.b64decode(first)
        except Exception as exc:  # pragma: no cover - defensive decode path
            raise TextToImageClientError("Could not decode ComfyUI image response.") from exc
