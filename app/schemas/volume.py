from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class VolumeCreate(BaseModel):
    name: str
    executor_id: int
    size_gb: Optional[int] = None


class VolumeUpdate(BaseModel):
    name: Optional[str] = None
    size_gb: Optional[int] = None


class VolumeResponse(BaseModel):
    id: int
    name: str
    executor_id: int
    size_gb: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VolumeMountRequest(BaseModel):
    volume_id: int
    mount_path: str = Field("/runpod-volume")


class VolumeMountResponse(BaseModel):
    id: int
    volume_id: int
    endpoint_id: int
    mount_path: str
    volume: VolumeResponse

    class Config:
        from_attributes = True


class EndpointVolumeInfo(BaseModel):
    """Volume info included in endpoint/executor update responses."""
    volume_id: int
    name: str
    mount_path: str
    size_gb: Optional[int] = None
