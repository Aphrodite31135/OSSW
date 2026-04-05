import io
import json
import uuid
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


class AssetPipeline:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def generate(
        self,
        image_bytes: bytes,
        original_name: str,
        resolution: int,
        height_scale: float,
        base_thickness: float,
    ) -> dict:
        job_id = uuid.uuid4().hex[:12]
        job_dir = self.output_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        source_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        source_image = ImageOps.exif_transpose(source_image)

        texture_image = self._prepare_texture(source_image, resolution)
        mask_image = self._build_foreground_mask(texture_image)
        depth_map = self._build_depth_map(texture_image, mask_image, height_scale, base_thickness)
        preview_image = self._build_preview(texture_image, depth_map, mask_image)

        texture_path = job_dir / "texture.png"
        preview_path = job_dir / "preview.png"
        obj_path = job_dir / "mesh.obj"
        mtl_path = job_dir / "mesh.mtl"
        metadata_path = job_dir / "metadata.json"
        zip_path = job_dir / "asset_package.zip"

        texture_image.save(texture_path)
        preview_image.save(preview_path)
        vertex_count, face_count = self._write_obj_with_mtl(
            depth_map=depth_map,
            obj_path=obj_path,
            mtl_path=mtl_path,
            texture_file_name=texture_path.name,
        )
        metadata = self._build_metadata(
            original_name=original_name,
            resolution=resolution,
            height_scale=height_scale,
            base_thickness=base_thickness,
            vertex_count=vertex_count,
            face_count=face_count,
        )
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        self._write_zip(zip_path, obj_path, mtl_path, texture_path, metadata_path, preview_path)

        stem = Path(original_name).stem or "asset"
        return {
            "job_id": job_id,
            "asset_name": f"{stem}_3d_asset.zip",
            "asset_url": f"/outputs/{job_id}/{zip_path.name}",
            "texture_url": f"/outputs/{job_id}/{texture_path.name}",
            "preview_url": f"/outputs/{job_id}/{preview_path.name}",
            "metadata_url": f"/outputs/{job_id}/{metadata_path.name}",
            "vertex_count": vertex_count,
            "face_count": face_count,
            "resolution": resolution,
            "height_scale": round(height_scale, 2),
            "base_thickness": round(base_thickness, 2),
            "summary": (
                "Generated a textured relief-style OBJ asset with a solid base, side walls, "
                "preview render, and metadata package."
            ),
        }

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
        original_name: str,
        resolution: int,
        height_scale: float,
        base_thickness: float,
        vertex_count: int,
        face_count: int,
    ) -> dict:
        return {
            "source_image": original_name,
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
        obj_path: Path,
        mtl_path: Path,
        texture_path: Path,
        metadata_path: Path,
        preview_path: Path,
    ) -> None:
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(obj_path, arcname=obj_path.name)
            archive.write(mtl_path, arcname=mtl_path.name)
            archive.write(texture_path, arcname=texture_path.name)
            archive.write(metadata_path, arcname=metadata_path.name)
            archive.write(preview_path, arcname=preview_path.name)
