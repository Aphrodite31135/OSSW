import http.client
from urllib import error, request


class CutoutClientError(RuntimeError):
    pass


class CutoutClient:
    def __init__(self, api_url: str, timeout_seconds: int = 900) -> None:
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds

    def isolate(self, image_bytes: bytes) -> bytes:
        req = request.Request(
            self.api_url,
            data=image_bytes,
            headers={"Content-Type": "application/octet-stream"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise CutoutClientError(f"Cutout API returned HTTP {exc.code}: {detail}") from exc
        except (error.URLError, http.client.RemoteDisconnected) as exc:
            raise CutoutClientError(f"Could not reach cutout API at {self.api_url}.") from exc

        if "application/json" in content_type:
            detail = body.decode("utf-8", errors="replace")
            raise CutoutClientError(f"Cutout API returned JSON instead of an image: {detail}")

        if not body:
            raise CutoutClientError("Cutout API returned an empty response.")

        return body
