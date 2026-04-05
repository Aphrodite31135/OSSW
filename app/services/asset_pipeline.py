import io
import uuid
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps


class AssetPipeline:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def generate(self, image_bytes: bytes, original_name: str) -> dict:
        job_id = uuid.uuid4().hex[:12]
        job_dir = self.output_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        source_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        source_image = ImageOps.exif_transpose(source_image)
        texture_image = self._prepare_texture(source_image)
        depth_map = self._build_depth_map(texture_image)

        texture_path = job_dir / "texture.png"
        preview_path = job_dir / "preview.png"
        obj_path = job_dir / "mesh.obj"
        mtl_path = job_dir / "mesh.mtl"
        zip_path = job_dir / "asset_package.zip"

        texture_image.save(texture_path)
        texture_image.save(preview_path)
        vertex_count, face_count = self._write_obj_with_mtl(depth_map, obj_path, mtl_path, texture_path.name)
        self._write_zip(zip_path, obj_path, mtl_path, texture_path)

        stem = Path(original_name).stem or "asset"
        return {
            "job_id": job_id,
            "asset_name": f"{stem}_3d_asset.zip",
            "asset_url": f"/outputs/{job_id}/{zip_path.name}",
            "texture_url": f"/outputs/{job_id}/{texture_path.name}",
            "preview_url": f"/outputs/{job_id}/{preview_path.name}",
            "vertex_count": vertex_count,
            "face_count": face_count,
            "summary": "Generated a height-map style OBJ asset package from the uploaded image.",
        }

    def _prepare_texture(self, image: Image.Image) -> Image.Image:
        image = ImageOps.contain(image, (128, 128))
        canvas = Image.new("RGB", (128, 128), color=(247, 243, 232))
        x = (canvas.width - image.width) // 2
        y = (canvas.height - image.height) // 2
        canvas.paste(image, (x, y))
        return canvas

    def _build_depth_map(self, image: Image.Image) -> np.ndarray:
        grayscale = ImageOps.grayscale(image)
        grayscale = grayscale.filter(ImageFilter.GaussianBlur(radius=1.2))
        normalized = np.asarray(grayscale, dtype=np.float32) / 255.0
        depth = 0.08 + (normalized * 0.42)
        return depth

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

        for y in range(rows):
            for x in range(cols):
                px = (x / (cols - 1)) - 0.5
                py = 0.5 - (y / (rows - 1))
                pz = float(depth_map[y, x])
                vertex_lines.append(f"v {px:.5f} {py:.5f} {pz:.5f}")
                uv_lines.append(f"vt {x / (cols - 1):.5f} {1 - (y / (rows - 1)):.5f}")

        def vertex_index(row: int, col: int) -> int:
            return row * cols + col + 1

        for y in range(rows - 1):
            for x in range(cols - 1):
                top_left = vertex_index(y, x)
                top_right = vertex_index(y, x + 1)
                bottom_left = vertex_index(y + 1, x)
                bottom_right = vertex_index(y + 1, x + 1)

                face_lines.append(
                    f"f {top_left}/{top_left} {bottom_left}/{bottom_left} {top_right}/{top_right}"
                )
                face_lines.append(
                    f"f {top_right}/{top_right} {bottom_left}/{bottom_left} {bottom_right}/{bottom_right}"
                )

        mtl_contents = "\n".join(
            [
                "newmtl material_0",
                "Kd 1.000 1.000 1.000",
                "Ka 0.200 0.200 0.200",
                "Ks 0.000 0.000 0.000",
                f"map_Kd {texture_file_name}",
                "",
            ]
        )
        mtl_path.write_text(mtl_contents, encoding="utf-8")

        obj_contents = "\n".join(
            [
                f"mtllib {mtl_path.name}",
                "o generated_mesh",
                "usemtl material_0",
                *vertex_lines,
                *uv_lines,
                *face_lines,
                "",
            ]
        )
        obj_path.write_text(obj_contents, encoding="utf-8")
        return len(vertex_lines), len(face_lines)

    def _write_zip(self, zip_path: Path, obj_path: Path, mtl_path: Path, texture_path: Path) -> None:
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(obj_path, arcname=obj_path.name)
            archive.write(mtl_path, arcname=mtl_path.name)
            archive.write(texture_path, arcname=texture_path.name)
