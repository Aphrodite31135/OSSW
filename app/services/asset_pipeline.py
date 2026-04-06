import io
import json
import uuid
import zipfile
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.services.cutout_client import CutoutClient, CutoutClientError
from app.services.real3d_client import Hunyuan3DClient, Real3DClientError
from app.services.text2image_client import TextToImageClient, TextToImageClientError
from app.settings import Settings


class AssetPipeline:
    def __init__(self, output_dir: Path, settings: Settings) -> None:
        self.output_dir = output_dir
        self.settings = settings

    def generate(
        self,
        source_mode: str,
        prompt: str | None,
        image_bytes: bytes | None,
        original_name: str,
        resolution: int,
        height_scale: float,
        base_thickness: float,
    ) -> dict:
        if source_mode == "text":
            image_bytes, original_name = self._generate_source_image_from_prompt(prompt)

        if image_bytes is None:
            raise ValueError("Image bytes are required after source preparation.")

        if self.settings.model_backend == "hunyuan_api":
            try:
                return self._generate_with_hunyuan_api(
                    source_mode=source_mode,
                    prompt=prompt,
                    image_bytes=image_bytes,
                    original_name=original_name,
                )
            except Real3DClientError:
                if not self.settings.fallback_to_relief:
                    raise

        return self._generate_relief_asset(
            source_mode=source_mode,
            prompt=prompt,
            image_bytes=image_bytes,
            original_name=original_name,
            resolution=resolution,
            height_scale=height_scale,
            base_thickness=base_thickness,
        )

    def _generate_source_image_from_prompt(self, prompt: str | None) -> tuple[bytes, str]:
        if not prompt:
            raise TextToImageClientError("A prompt is required for text-to-image generation.")
        if self.settings.text_to_image_backend not in {"flux_api", "openai_image_api", "comfyui_api"}:
            raise TextToImageClientError(
                "Text-to-image backend is not enabled. Set TEXT_TO_IMAGE_BACKEND=flux_api, openai_image_api, or comfyui_api first."
            )

        client = TextToImageClient(
            api_url=self.settings.text_to_image_api_url,
            timeout_seconds=self.settings.text_to_image_timeout_seconds,
            api_key=self.settings.text_to_image_api_key,
        )
        image_bytes = client.generate_image(prompt=prompt, backend=self.settings.text_to_image_backend)
        image_bytes = self._apply_cutout_if_enabled(image_bytes)
        return image_bytes, "prompt_generated.png"

    def _apply_cutout_if_enabled(self, image_bytes: bytes) -> bytes:
        if not self.settings.cutout_backend_enabled:
            return image_bytes

        client = CutoutClient(
            api_url=self.settings.cutout_api_url,
            timeout_seconds=self.settings.cutout_timeout_seconds,
        )
        try:
            return client.isolate(image_bytes)
        except CutoutClientError:
            return image_bytes

    def _generate_relief_asset(
        self,
        source_mode: str,
        prompt: str | None,
        image_bytes: bytes,
        original_name: str,
        resolution: int,
        height_scale: float,
        base_thickness: float,
    ) -> dict:
        job_id = uuid.uuid4().hex[:12]
        job_dir = self.output_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        source_image = self._load_source_image(image_bytes)
        source_image = self._composite_for_preview(source_image)

        texture_image = self._prepare_texture(source_image, resolution)
        mask_image = self._build_foreground_mask(texture_image)
        depth_map = self._build_depth_map(texture_image, mask_image, height_scale, base_thickness)
        preview_image = self._build_preview(texture_image, depth_map, mask_image)
        gray_render_image = self._build_gray_render(depth_map, mask_image)

        source_image_path = job_dir / "source_input.png"
        texture_path = job_dir / "texture.png"
        preview_path = job_dir / "preview.png"
        gray_render_path = job_dir / "gray_render.png"
        obj_path = job_dir / "mesh.obj"
        mtl_path = job_dir / "mesh.mtl"
        metadata_path = job_dir / "metadata.json"
        zip_path = job_dir / "asset_package.zip"

        source_image.save(source_image_path)
        texture_image.save(texture_path)
        preview_image.save(preview_path)
        gray_render_image.save(gray_render_path)
        vertex_count, face_count = self._write_obj_with_mtl(
            depth_map=depth_map,
            obj_path=obj_path,
            mtl_path=mtl_path,
            texture_file_name=texture_path.name,
        )
        metadata = self._build_metadata(
            source_mode=source_mode,
            prompt=prompt,
            original_name=original_name,
            resolution=resolution,
            height_scale=height_scale,
            base_thickness=base_thickness,
            vertex_count=vertex_count,
            face_count=face_count,
        )
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        self._write_zip(
            zip_path,
            source_image_path,
            obj_path,
            mtl_path,
            texture_path,
            metadata_path,
            preview_path,
            gray_render_path,
        )

        stem = Path(original_name).stem or "asset"
        return {
            "job_id": job_id,
            "source_mode": source_mode,
            "backend": "relief",
            "asset_format": "zip+obj",
            "asset_name": f"{stem}_3d_asset.zip",
            "asset_url": f"/outputs/{job_id}/{zip_path.name}",
            "source_image_url": f"/outputs/{job_id}/{source_image_path.name}",
            "prompt": prompt,
            "texture_url": f"/outputs/{job_id}/{texture_path.name}",
            "preview_url": f"/outputs/{job_id}/{preview_path.name}",
            "gray_render_url": f"/outputs/{job_id}/{gray_render_path.name}",
            "metadata_url": f"/outputs/{job_id}/{metadata_path.name}",
            "vertex_count": vertex_count,
            "face_count": face_count,
            "resolution": resolution,
            "height_scale": round(height_scale, 2),
            "base_thickness": round(base_thickness, 2),
            "summary": (
                "Generated a textured relief-style OBJ asset with a solid base, side walls, "
                "color preview, grayscale shaded render, and metadata package."
            ),
        }

    def _generate_with_hunyuan_api(
        self,
        source_mode: str,
        prompt: str | None,
        image_bytes: bytes,
        original_name: str,
    ) -> dict:
        job_id = uuid.uuid4().hex[:12]
        job_dir = self.output_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        source_image = self._load_source_image(image_bytes)
        source_image = ImageOps.exif_transpose(source_image)
        prepared_input = self._prepare_hunyuan_input(source_image, source_mode)
        preview_image = self._composite_for_preview(prepared_input)
        gray_render_image = ImageOps.grayscale(preview_image).convert("RGB")

        source_input_path = job_dir / "source_input.png"
        input_path = job_dir / "input.png"
        preview_path = job_dir / "preview.png"
        gray_render_path = job_dir / "gray_render.png"
        glb_path = job_dir / "model.glb"
        metadata_path = job_dir / "metadata.json"
        zip_path = job_dir / "asset_package.zip"

        self._composite_for_preview(source_image).save(source_input_path)
        prepared_input.save(input_path)
        preview_image.save(preview_path)
        gray_render_image.save(gray_render_path)

        client = Hunyuan3DClient(
            api_url=self.settings.hunyuan3d_api_url,
            timeout_seconds=self.settings.hunyuan3d_timeout_seconds,
        )
        glb_path.write_bytes(client.generate_glb(input_path.read_bytes()))

        metadata = {
            "source_image": original_name,
            "source_mode": source_mode,
            "prompt": prompt,
            "pipeline_version": "real-image-to-3d-v1.0",
            "backend": "hunyuan_api",
            "asset_type": "glb",
            "backend_url": self.settings.hunyuan3d_api_url,
            "notes": [
                "Generated by an external real image-to-3D model backend.",
                "This path is designed for desktop GPU inference and future text-to-image-to-3D expansion.",
                "Text-to-image mode uses a prompt template and extra padding so the full object stays in frame for 3D reconstruction.",
            ],
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(glb_path, arcname=glb_path.name)
            archive.write(source_input_path, arcname=source_input_path.name)
            archive.write(preview_path, arcname=preview_path.name)
            archive.write(gray_render_path, arcname=gray_render_path.name)
            archive.write(metadata_path, arcname=metadata_path.name)

        stem = Path(original_name).stem or "asset"
        return {
            "job_id": job_id,
            "source_mode": source_mode,
            "backend": "hunyuan_api",
            "asset_format": "zip+glb",
            "asset_name": f"{stem}_3d_asset.zip",
            "asset_url": f"/outputs/{job_id}/{zip_path.name}",
            "source_image_url": f"/outputs/{job_id}/{source_input_path.name}",
            "prompt": prompt,
            "preview_url": f"/outputs/{job_id}/{preview_path.name}",
            "gray_render_url": f"/outputs/{job_id}/{gray_render_path.name}",
            "metadata_url": f"/outputs/{job_id}/{metadata_path.name}",
            "summary": (
                "Generated a GLB asset through the text/image-to-3D backend path. "
                "The package includes the model file, source image, preview image, grayscale render, and metadata."
            ),
        }

    def _prepare_hunyuan_input(self, image: Image.Image, source_mode: str) -> Image.Image:
        if source_mode == "text":
            if image.mode == "RGBA":
                isolated = self._trim_alpha_pedestal(image)
            else:
                isolated = self._extract_primary_object(image)
            canvas = self._fit_object_to_canvas(isolated, canvas_size=512, target_fill=0.66)
            if canvas.mode == "RGBA":
                rgb = self._composite_for_preview(canvas)
                rgb = ImageEnhance.Contrast(rgb).enhance(1.03)
                alpha = canvas.getchannel("A")
                return Image.merge("RGBA", (*rgb.split(), alpha))

            canvas = ImageEnhance.Contrast(canvas).enhance(1.03)
            return canvas

        return self._prepare_texture(image, 512)

    def _load_source_image(self, image_bytes: bytes) -> Image.Image:
        image = Image.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image)
        return image.convert("RGBA") if "A" in image.getbands() else image.convert("RGB")

    def _extract_primary_object(self, image: Image.Image) -> Image.Image:
        rgb = image.convert("RGB")
        arr = np.asarray(rgb, dtype=np.float32)

        border = np.concatenate(
            [
                arr[0, :, :],
                arr[-1, :, :],
                arr[:, 0, :],
                arr[:, -1, :],
            ],
            axis=0,
        )
        bg = np.median(border, axis=0)
        base_mask = self._build_object_mask(rgb, arr, bg)
        if not np.any(base_mask):
            return rgb

        focused_mask = self._focus_central_object(base_mask)
        main_mask = self._select_main_component(focused_mask)
        if main_mask is None:
            main_mask = self._select_main_component(base_mask)
        if main_mask is None:
            return rgb

        main_mask = self._trim_ground_plane(main_mask)
        trimmed_mask = self._retain_vertical_core(main_mask)
        if np.count_nonzero(trimmed_mask) >= np.count_nonzero(main_mask) * 0.42:
            main_mask = trimmed_mask

        ys, xs = np.where(main_mask)
        top = int(ys.min())
        bottom = int(ys.max()) + 1
        left = int(xs.min())
        right = int(xs.max()) + 1

        cropped = rgb.crop((left, top, right, bottom))
        cropped_mask = main_mask[top:bottom, left:right]

        cropped_arr = np.asarray(cropped, dtype=np.uint8)
        alpha = np.where(cropped_mask, 255, 0).astype(np.uint8)
        rgba = np.dstack((cropped_arr, alpha))
        return Image.fromarray(rgba, mode="RGBA")

    def _focus_central_object(self, mask: np.ndarray) -> np.ndarray:
        h, w = mask.shape
        focused = np.zeros_like(mask, dtype=bool)
        left = int(w * 0.16)
        right = int(w * 0.84)
        top = int(h * 0.03)
        bottom = int(h * 0.97)
        focused[top:bottom, left:right] = mask[top:bottom, left:right]
        return focused if np.count_nonzero(focused) >= max(250, np.count_nonzero(mask) * 0.18) else mask

    def _composite_for_preview(self, image: Image.Image) -> Image.Image:
        if image.mode != "RGBA":
            return image.convert("RGB")

        bg = Image.new("RGB", image.size, color=(209, 208, 219))
        bg.paste(image, mask=image.getchannel("A"))
        return bg

    def _trim_alpha_pedestal(self, image: Image.Image) -> Image.Image:
        rgba = image.convert("RGBA")
        alpha = np.asarray(rgba.getchannel("A"), dtype=np.uint8)
        mask = alpha > 10
        rows = np.where(mask.any(axis=1))[0]
        if rows.size == 0:
            return rgba

        top = int(rows[0])
        bottom = int(rows[-1])
        h, w = mask.shape
        comp_height = bottom - top + 1
        if comp_height < 80:
            return rgba

        widths = np.zeros(h, dtype=np.int32)
        for y in rows:
            xs = np.where(mask[y])[0]
            if xs.size:
                widths[y] = int(xs.max()) - int(xs.min()) + 1

        body_top = top + int(comp_height * 0.2)
        body_bottom = top + int(comp_height * 0.7)
        ref_widths = widths[body_top:body_bottom]
        ref_widths = ref_widths[ref_widths > 0]
        if ref_widths.size == 0:
            return rgba

        ref_width = float(np.median(ref_widths))
        trim_start = None
        for y in range(top + int(comp_height * 0.7), bottom):
            width = widths[y]
            if width <= 0:
                continue
            if width > ref_width * 1.18:
                trim_start = y
                break

        if trim_start is None:
            return rgba

        refined = alpha.copy()
        support = mask[max(top, trim_start - 24) : trim_start, :].any(axis=0)
        if support.any():
            support_cols = np.where(support)[0]
            left = max(0, int(support_cols.min()) - 6)
            right = min(w - 1, int(support_cols.max()) + 6)
            refined[trim_start:, :left] = 0
            refined[trim_start:, right + 1 :] = 0

        out = rgba.copy()
        out.putalpha(Image.fromarray(refined, mode="L"))
        return out

    def _build_object_mask(self, image: Image.Image, arr: np.ndarray, bg: np.ndarray) -> np.ndarray:
        gray = np.asarray(ImageOps.grayscale(image).filter(ImageFilter.GaussianBlur(radius=1.2)), dtype=np.float32) / 255.0
        edge_y, edge_x = np.gradient(gray)
        edge_strength = np.hypot(edge_x, edge_y)
        bg_dist = np.linalg.norm(arr - bg, axis=2)

        strong_foreground = bg_dist > 18.0
        edge_barrier = edge_strength > 0.032
        barrier = strong_foreground | edge_barrier
        barrier = self._dilate_mask(barrier, iterations=1)

        outside = self._flood_background(~barrier)
        mask = ~outside
        mask |= strong_foreground
        mask = self._close_mask(mask, iterations=2)
        mask = self._fill_mask_holes(mask)
        return mask

    def _trim_ground_plane(self, mask: np.ndarray) -> np.ndarray:
        h, w = mask.shape
        rows = np.where(mask.any(axis=1))[0]
        if rows.size == 0:
            return mask

        top = int(rows[0])
        bottom = int(rows[-1])
        comp_height = bottom - top + 1
        if comp_height < 80:
            return mask

        widths = np.zeros(h, dtype=np.int32)
        lefts = np.full(h, -1, dtype=np.int32)
        rights = np.full(h, -1, dtype=np.int32)
        for y in rows:
            xs = np.where(mask[y])[0]
            if xs.size:
                lefts[y] = int(xs.min())
                rights[y] = int(xs.max())
                widths[y] = rights[y] - lefts[y] + 1

        search_start = top + int(comp_height * 0.45)
        search_end = bottom - max(6, int(comp_height * 0.05))
        cutoff = None
        best_gain = 0.0
        for y in range(search_start, search_end):
            if widths[y] <= 0:
                continue
            below = widths[y + 1 : min(bottom + 1, y + 7)]
            below = below[below > 0]
            if below.size < 2:
                continue

            gain = float(np.median(below) - widths[y])
            relative_gain = gain / max(1.0, float(widths[y]))
            if gain > best_gain and gain > 18.0 and relative_gain > 0.12:
                best_gain = gain
                cutoff = y

        if cutoff is None:
            return mask

        refined = mask.copy()
        support_margin = max(6, int(widths[cutoff] * 0.04))
        for y in range(cutoff + 1, bottom + 1):
            above = refined[max(top, y - 18) : y, :]
            supported_cols = above.any(axis=0)
            row_cols = np.where(refined[y])[0]
            if row_cols.size == 0:
                continue

            keep = supported_cols[row_cols]
            if support_margin > 0 and supported_cols.any():
                supported_idx = np.where(supported_cols)[0]
                left_bound = int(supported_idx.min()) - support_margin
                right_bound = int(supported_idx.max()) + support_margin
                keep = keep | ((row_cols >= left_bound) & (row_cols <= right_bound))

            refined[y, row_cols[~keep]] = False

        final_mask = self._select_main_component(refined)
        return final_mask if final_mask is not None else mask

    def _retain_vertical_core(self, mask: np.ndarray) -> np.ndarray:
        h, w = mask.shape
        rows = np.where(mask.any(axis=1))[0]
        if rows.size == 0:
            return mask

        top = int(rows[0])
        bottom = int(rows[-1])
        comp_height = bottom - top + 1
        if comp_height < 96:
            return mask

        row_center = (w - 1) / 2.0
        search_top = top + int(comp_height * 0.08)
        search_bottom = top + int(comp_height * 0.72)

        ref_centers: list[float] = []
        ref_widths: list[float] = []
        for y in range(search_top, min(bottom + 1, search_bottom)):
            spans = self._row_spans(mask[y])
            if not spans:
                continue

            span = min(spans, key=lambda s: abs(((s[0] + s[1]) / 2.0) - row_center))
            width = span[1] - span[0] + 1
            if width < max(18, w * 0.06):
                continue

            ref_centers.append((span[0] + span[1]) / 2.0)
            ref_widths.append(float(width))

        if not ref_centers:
            return mask

        ref_center = float(np.median(np.asarray(ref_centers, dtype=np.float32)))
        ref_width = float(np.percentile(np.asarray(ref_widths, dtype=np.float32), 65))
        if ref_width <= 0:
            return mask

        max_center_shift = max(28.0, ref_width * 0.42)
        lower_row_start = top + int(comp_height * 0.68)
        refined = np.zeros_like(mask, dtype=bool)

        for y in rows:
            spans = self._row_spans(mask[y])
            if not spans:
                continue

            dynamic_width_cap = ref_width * (1.65 if y < lower_row_start else 1.15)
            dynamic_center_shift = max_center_shift * (1.18 if y < lower_row_start else 0.92)

            candidates: list[tuple[float, tuple[int, int]]] = []
            for span in spans:
                width = span[1] - span[0] + 1
                center = (span[0] + span[1]) / 2.0
                center_delta = abs(center - ref_center)
                if width > dynamic_width_cap or center_delta > dynamic_center_shift:
                    continue

                score = center_delta + max(0.0, width - ref_width) * 0.35
                candidates.append((score, span))

            chosen = min(candidates, key=lambda item: item[0])[1] if candidates else None
            if chosen is None:
                span = min(spans, key=lambda s: abs(((s[0] + s[1]) / 2.0) - ref_center))
                width = span[1] - span[0] + 1
                center = (span[0] + span[1]) / 2.0
                if width > ref_width * 1.9 or abs(center - ref_center) > max_center_shift * 1.5:
                    continue
                chosen = span

            refined[y, chosen[0] : chosen[1] + 1] = True

        final_mask = self._select_main_component(refined)
        return final_mask if final_mask is not None else mask

    def _dilate_mask(self, mask: np.ndarray, iterations: int) -> np.ndarray:
        result = mask.copy()
        for _ in range(max(0, iterations)):
            padded = np.pad(result, 1, mode="constant", constant_values=False)
            expanded = np.zeros_like(result, dtype=bool)
            for dy in range(3):
                for dx in range(3):
                    expanded |= padded[dy : dy + result.shape[0], dx : dx + result.shape[1]]
            result = expanded
        return result

    def _erode_mask(self, mask: np.ndarray, iterations: int) -> np.ndarray:
        result = mask.copy()
        for _ in range(max(0, iterations)):
            padded = np.pad(result, 1, mode="constant", constant_values=False)
            shrunk = np.ones_like(result, dtype=bool)
            for dy in range(3):
                for dx in range(3):
                    shrunk &= padded[dy : dy + result.shape[0], dx : dx + result.shape[1]]
            result = shrunk
        return result

    def _close_mask(self, mask: np.ndarray, iterations: int) -> np.ndarray:
        return self._erode_mask(self._dilate_mask(mask, iterations), iterations)

    def _fill_mask_holes(self, mask: np.ndarray) -> np.ndarray:
        outside = self._flood_background(~mask)
        holes = (~mask) & (~outside)
        return mask | holes

    def _flood_background(self, passable: np.ndarray) -> np.ndarray:
        h, w = passable.shape
        visited = np.zeros_like(passable, dtype=bool)
        queue: deque[tuple[int, int]] = deque()

        for x in range(w):
            if passable[0, x] and not visited[0, x]:
                visited[0, x] = True
                queue.append((0, x))
            if passable[h - 1, x] and not visited[h - 1, x]:
                visited[h - 1, x] = True
                queue.append((h - 1, x))

        for y in range(h):
            if passable[y, 0] and not visited[y, 0]:
                visited[y, 0] = True
                queue.append((y, 0))
            if passable[y, w - 1] and not visited[y, w - 1]:
                visited[y, w - 1] = True
                queue.append((y, w - 1))

        while queue:
            cy, cx = queue.popleft()
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < h and 0 <= nx < w and passable[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((ny, nx))

        return visited

    def _row_spans(self, row_mask: np.ndarray) -> list[tuple[int, int]]:
        xs = np.where(row_mask)[0]
        if xs.size == 0:
            return []

        spans: list[tuple[int, int]] = []
        start = int(xs[0])
        prev = int(xs[0])
        for value in xs[1:]:
            x = int(value)
            if x != prev + 1:
                spans.append((start, prev))
                start = x
            prev = x
        spans.append((start, prev))
        return spans

    def _select_main_component(self, mask: np.ndarray) -> np.ndarray | None:
        h, w = mask.shape
        visited = np.zeros((h, w), dtype=bool)
        best_component: list[tuple[int, int]] | None = None
        best_score = float("-inf")
        center_y = (h - 1) / 2.0
        center_x = (w - 1) / 2.0

        for y in range(h):
            for x in range(w):
                if not mask[y, x] or visited[y, x]:
                    continue

                queue: deque[tuple[int, int]] = deque([(y, x)])
                visited[y, x] = True
                pixels: list[tuple[int, int]] = []
                touches_border = False

                while queue:
                    cy, cx = queue.popleft()
                    pixels.append((cy, cx))
                    if cy == 0 or cx == 0 or cy == h - 1 or cx == w - 1:
                        touches_border = True

                    for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            queue.append((ny, nx))

                area = len(pixels)
                if area < max(200, (h * w) // 500):
                    continue

                ys = np.array([p[0] for p in pixels], dtype=np.float32)
                xs = np.array([p[1] for p in pixels], dtype=np.float32)
                cy = float(ys.mean())
                cx = float(xs.mean())
                distance = ((cy - center_y) ** 2 + (cx - center_x) ** 2) ** 0.5
                diagonal = (h**2 + w**2) ** 0.5

                score = area - (distance / diagonal) * (h * w * 0.18)
                if touches_border:
                    score *= 0.92

                if score > best_score:
                    best_score = score
                    best_component = pixels

        if best_component is None:
            return None

        result = np.zeros_like(mask, dtype=bool)
        for y, x in best_component:
            result[y, x] = True
        return result

    def _fit_object_to_canvas(self, image: Image.Image, canvas_size: int, target_fill: float) -> Image.Image:
        if image.mode == "RGBA":
            rgba = image
            alpha = np.asarray(rgba.getchannel("A"), dtype=np.uint8)
            mask = alpha > 8
            bg_color = (0, 0, 0, 0)
        else:
            rgb = image.convert("RGB")
            arr = np.asarray(rgb, dtype=np.float32)

            # Estimate the background from the image border so we can recover a rough object bbox.
            border = np.concatenate(
                [
                    arr[0, :, :],
                    arr[-1, :, :],
                    arr[:, 0, :],
                    arr[:, -1, :],
                ],
                axis=0,
            )
            bg = np.median(border, axis=0)
            dist = np.linalg.norm(arr - bg, axis=2)
            mask = dist > 18.0
            rgba = rgb.convert("RGBA")
            bg_color = tuple(int(v) for v in bg) + (255,)

        if not np.any(mask):
            fitted = ImageOps.contain(rgba, (int(canvas_size * target_fill), int(canvas_size * target_fill)))
            canvas = Image.new("RGBA", (canvas_size, canvas_size), color=bg_color)
            x = (canvas.width - fitted.width) // 2
            y = (canvas.height - fitted.height) // 2
            canvas.alpha_composite(fitted, (x, y))
            return canvas

        coords = np.argwhere(mask)
        top, left = coords.min(axis=0)
        bottom, right = coords.max(axis=0) + 1
        cropped = rgba.crop((int(left), int(top), int(right), int(bottom)))

        max_side = max(cropped.width, cropped.height)
        target_side = max(1, int(canvas_size * target_fill))
        scale = target_side / max_side
        resized = cropped.resize(
            (
                max(1, int(round(cropped.width * scale))),
                max(1, int(round(cropped.height * scale))),
            ),
            Image.Resampling.LANCZOS,
        )

        canvas = Image.new("RGBA", (canvas_size, canvas_size), color=bg_color)
        x = (canvas.width - resized.width) // 2
        y = (canvas.height - resized.height) // 2
        canvas.alpha_composite(resized, (x, y))
        return canvas

    def _prepare_texture(self, image: Image.Image, resolution: int) -> Image.Image:
        image = ImageOps.contain(image, (resolution, resolution))
        canvas = Image.new("RGB", (resolution, resolution), color=(246, 241, 230))
        x = (canvas.width - image.width) // 2
        y = (canvas.height - image.height) // 2
        canvas.paste(image, (x, y))
        canvas = ImageEnhance.Color(canvas).enhance(1.08)
        canvas = ImageEnhance.Contrast(canvas).enhance(1.06)
        return canvas

    def _build_foreground_mask(self, image: Image.Image) -> Image.Image:
        grayscale = ImageOps.grayscale(image)
        inverted = ImageOps.invert(grayscale)
        softened = inverted.filter(ImageFilter.GaussianBlur(radius=2.4))
        boosted = ImageEnhance.Contrast(softened).enhance(1.8)
        return boosted

    def _build_depth_map(
        self,
        image: Image.Image,
        mask_image: Image.Image,
        height_scale: float,
        base_thickness: float,
    ) -> np.ndarray:
        grayscale = ImageOps.grayscale(image)
        smooth = grayscale.filter(ImageFilter.GaussianBlur(radius=1.6))
        edges = grayscale.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(radius=1.1))

        tone = np.asarray(smooth, dtype=np.float32) / 255.0
        detail = np.asarray(edges, dtype=np.float32) / 255.0
        mask = np.asarray(mask_image, dtype=np.float32) / 255.0
        mask = np.clip(mask * 1.2, 0.15, 1.0)

        blended = (0.72 * tone) + (0.28 * detail)
        normalized = (blended - blended.min()) / (blended.max() - blended.min() + 1e-6)
        depth = base_thickness + (normalized * mask * height_scale)
        return depth.astype(np.float32)

    def _build_preview(self, texture_image: Image.Image, depth_map: np.ndarray, mask_image: Image.Image) -> Image.Image:
        texture = np.asarray(texture_image, dtype=np.float32)
        mask = np.asarray(mask_image, dtype=np.float32) / 255.0
        gy, gx = np.gradient(depth_map)
        light = 0.86 + (gx * 0.9) - (gy * 1.2)
        light = np.clip(light, 0.58, 1.28)
        alpha = np.clip(0.25 + (mask * 0.75), 0.3, 1.0)[..., None]

        shaded = texture * light[..., None]
        lifted = shaded * alpha + (245.0 * (1.0 - alpha))
        return Image.fromarray(np.uint8(np.clip(lifted, 0, 255)), mode="RGB")

    def _build_gray_render(self, depth_map: np.ndarray, mask_image: Image.Image) -> Image.Image:
        mask = np.asarray(mask_image, dtype=np.float32) / 255.0
        gy, gx = np.gradient(depth_map)
        slope_light = 0.9 + (gx * 1.45) - (gy * 1.7)
        slope_light = np.clip(slope_light, 0.42, 1.18)

        base_gray = 196.0 + (slope_light * 34.0)
        shadow = np.clip(1.0 - mask, 0.0, 0.78) * 28.0
        ridge = np.clip(depth_map / (float(depth_map.max()) + 1e-6), 0.0, 1.0) * 16.0
        render = base_gray + ridge - shadow
        render = np.clip(render, 82.0, 242.0)

        # Slightly offset darker shadow for a more readable report-style render.
        shifted_shadow = np.roll(mask, shift=(4, 6), axis=(0, 1))
        shifted_shadow = (1.0 - shifted_shadow) * 38.0
        render = np.clip(render - shifted_shadow, 70.0, 242.0)

        rgb = np.repeat(render[..., None], 3, axis=2)
        return Image.fromarray(np.uint8(rgb), mode="RGB")

    def _write_obj_with_mtl(
        self,
        depth_map: np.ndarray,
        obj_path: Path,
        mtl_path: Path,
        texture_file_name: str,
    ) -> tuple[int, int]:
        rows, cols = depth_map.shape
        vertex_lines: list[str] = []
        uv_lines: list[str] = []
        face_lines: list[str] = []

        def add_vertex(x: float, y: float, z: float) -> int:
            vertex_lines.append(f"v {x:.5f} {y:.5f} {z:.5f}")
            return len(vertex_lines)

        def add_uv(u: float, v: float) -> int:
            uv_lines.append(f"vt {u:.5f} {v:.5f}")
            return len(uv_lines)

        top_vertices: list[list[int]] = []
        top_uvs: list[list[int]] = []
        bottom_vertices: list[list[int]] = []

        for row in range(rows):
            top_row: list[int] = []
            uv_row: list[int] = []
            bottom_row: list[int] = []
            for col in range(cols):
                px = (col / (cols - 1)) - 0.5
                py = 0.5 - (row / (rows - 1))
                pz = float(depth_map[row, col])
                top_row.append(add_vertex(px, py, pz))
                uv_row.append(add_uv(col / (cols - 1), 1 - (row / (rows - 1))))
                bottom_row.append(add_vertex(px, py, 0.0))
            top_vertices.append(top_row)
            top_uvs.append(uv_row)
            bottom_vertices.append(bottom_row)

        def add_face(v1: int, v2: int, v3: int, t1: int, t2: int, t3: int) -> None:
            face_lines.append(f"f {v1}/{t1} {v2}/{t2} {v3}/{t3}")

        for row in range(rows - 1):
            for col in range(cols - 1):
                top_left = top_vertices[row][col]
                top_right = top_vertices[row][col + 1]
                bottom_left = top_vertices[row + 1][col]
                bottom_right = top_vertices[row + 1][col + 1]

                uv_top_left = top_uvs[row][col]
                uv_top_right = top_uvs[row][col + 1]
                uv_bottom_left = top_uvs[row + 1][col]
                uv_bottom_right = top_uvs[row + 1][col + 1]

                add_face(top_left, bottom_left, top_right, uv_top_left, uv_bottom_left, uv_top_right)
                add_face(top_right, bottom_left, bottom_right, uv_top_right, uv_bottom_left, uv_bottom_right)

                base_top_left = bottom_vertices[row][col]
                base_top_right = bottom_vertices[row][col + 1]
                base_bottom_left = bottom_vertices[row + 1][col]
                base_bottom_right = bottom_vertices[row + 1][col + 1]

                add_face(base_top_left, base_top_right, base_bottom_left, uv_top_left, uv_top_right, uv_bottom_left)
                add_face(base_top_right, base_bottom_right, base_bottom_left, uv_top_right, uv_bottom_right, uv_bottom_left)

        for row in range(rows - 1):
            left_uv_top = top_uvs[row][0]
            left_uv_bottom = top_uvs[row + 1][0]
            right_uv_top = top_uvs[row][cols - 1]
            right_uv_bottom = top_uvs[row + 1][cols - 1]

            add_face(
                top_vertices[row][0],
                bottom_vertices[row][0],
                top_vertices[row + 1][0],
                left_uv_top,
                left_uv_top,
                left_uv_bottom,
            )
            add_face(
                top_vertices[row + 1][0],
                bottom_vertices[row][0],
                bottom_vertices[row + 1][0],
                left_uv_bottom,
                left_uv_top,
                left_uv_bottom,
            )

            add_face(
                top_vertices[row][cols - 1],
                top_vertices[row + 1][cols - 1],
                bottom_vertices[row][cols - 1],
                right_uv_top,
                right_uv_bottom,
                right_uv_top,
            )
            add_face(
                top_vertices[row + 1][cols - 1],
                bottom_vertices[row + 1][cols - 1],
                bottom_vertices[row][cols - 1],
                right_uv_bottom,
                right_uv_bottom,
                right_uv_top,
            )

        for col in range(cols - 1):
            top_uv_left = top_uvs[0][col]
            top_uv_right = top_uvs[0][col + 1]
            bottom_uv_left = top_uvs[rows - 1][col]
            bottom_uv_right = top_uvs[rows - 1][col + 1]

            add_face(
                top_vertices[0][col],
                top_vertices[0][col + 1],
                bottom_vertices[0][col],
                top_uv_left,
                top_uv_right,
                top_uv_left,
            )
            add_face(
                top_vertices[0][col + 1],
                bottom_vertices[0][col + 1],
                bottom_vertices[0][col],
                top_uv_right,
                top_uv_right,
                top_uv_left,
            )

            add_face(
                top_vertices[rows - 1][col],
                bottom_vertices[rows - 1][col],
                top_vertices[rows - 1][col + 1],
                bottom_uv_left,
                bottom_uv_left,
                bottom_uv_right,
            )
            add_face(
                top_vertices[rows - 1][col + 1],
                bottom_vertices[rows - 1][col],
                bottom_vertices[rows - 1][col + 1],
                bottom_uv_right,
                bottom_uv_left,
                bottom_uv_right,
            )

        mtl_contents = "\n".join(
            [
                "newmtl material_0",
                "Kd 1.000 1.000 1.000",
                "Ka 0.200 0.200 0.200",
                "Ks 0.080 0.080 0.080",
                f"map_Kd {texture_file_name}",
                "",
            ]
        )
        mtl_path.write_text(mtl_contents, encoding="utf-8")

        obj_contents = "\n".join(
            [
                f"mtllib {mtl_path.name}",
                "o generated_relief_asset",
                "usemtl material_0",
                *vertex_lines,
                *uv_lines,
                *face_lines,
                "",
            ]
        )
        obj_path.write_text(obj_contents, encoding="utf-8")
        return len(vertex_lines), len(face_lines)

    def _build_metadata(
        self,
        source_mode: str,
        prompt: str | None,
        original_name: str,
        resolution: int,
        height_scale: float,
        base_thickness: float,
        vertex_count: int,
        face_count: int,
    ) -> dict:
        return {
            "source_image": original_name,
            "source_mode": source_mode,
            "prompt": prompt,
            "pipeline_version": "image-to-3d-v1.0",
            "asset_type": "textured-relief-obj",
            "resolution": resolution,
            "height_scale": round(height_scale, 3),
            "base_thickness": round(base_thickness, 3),
            "vertex_count": vertex_count,
            "face_count": face_count,
            "notes": [
                "Generated from a single reference image.",
                "Mesh includes a solid base and side walls for easier demo viewing.",
                "Designed as a lightweight homework-friendly placeholder for a future GPU 3D model pipeline.",
            ],
        }

    def _write_zip(
        self,
        zip_path: Path,
        source_image_path: Path,
        obj_path: Path,
        mtl_path: Path,
        texture_path: Path,
        metadata_path: Path,
        preview_path: Path,
        gray_render_path: Path,
    ) -> None:
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(source_image_path, arcname=source_image_path.name)
            archive.write(obj_path, arcname=obj_path.name)
            archive.write(mtl_path, arcname=mtl_path.name)
            archive.write(texture_path, arcname=texture_path.name)
            archive.write(metadata_path, arcname=metadata_path.name)
            archive.write(preview_path, arcname=preview_path.name)
            archive.write(gray_render_path, arcname=gray_render_path.name)
