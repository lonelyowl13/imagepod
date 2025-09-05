from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class JobTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    docker_image: str
    docker_tag: str = "latest"
    template_config: Optional[Dict[str, Any]] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    min_gpu_memory: Optional[int] = None
    max_gpu_memory: Optional[int] = None
    min_cpu_cores: Optional[int] = None
    max_cpu_cores: Optional[int] = None
    min_ram: Optional[int] = None
    max_ram: Optional[int] = None
    base_price_per_second: float = 0.0
    is_public: bool = False


class JobTemplateCreate(JobTemplateBase):
    pass


class JobTemplateResponse(JobTemplateBase):
    id: int
    is_active: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_id: Optional[int] = None
    input_data: Optional[Dict[str, Any]] = None


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class JobResponse(JobBase):
    id: int
    user_id: int
    status: str
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    worker_id: Optional[int] = None
    worker_pool_id: Optional[int] = None
    gpu_memory_used: Optional[int] = None
    cpu_cores_used: Optional[int] = None
    ram_used: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    cost: float
    billing_account_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobStatusUpdate(BaseModel):
    status: str
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    gpu_memory_used: Optional[int] = None
    cpu_cores_used: Optional[int] = None
    ram_used: Optional[int] = None
    duration_seconds: Optional[float] = None
