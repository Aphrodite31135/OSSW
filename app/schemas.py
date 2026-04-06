from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class AssetResponse(BaseModel):
    job_id: str
    source_mode: str
    backend: str
    asset_format: str
    asset_name: str
    asset_url: str
    source_image_url: Optional[str] = None
    prompt: Optional[str] = None
    texture_url: Optional[str] = None
    preview_url: Optional[str] = None
    gray_render_url: Optional[str] = None
    metadata_url: Optional[str] = None
    vertex_count: Optional[int] = None
    face_count: Optional[int] = None
    resolution: Optional[int] = None
    height_scale: Optional[float] = None
    base_thickness: Optional[float] = None
    summary: str
