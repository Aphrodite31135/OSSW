from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class AssetResponse(BaseModel):
    job_id: str
    asset_name: str
    asset_url: str
    texture_url: str
    preview_url: str
    gray_render_url: str
    metadata_url: str
    vertex_count: int
    face_count: int
    resolution: int
    height_scale: float
    base_thickness: float
    summary: str
