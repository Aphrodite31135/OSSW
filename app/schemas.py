from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class AssetResponse(BaseModel):
    job_id: str
    asset_name: str
    asset_url: str
    texture_url: str
    preview_url: str
    vertex_count: int
    face_count: int
    summary: str
