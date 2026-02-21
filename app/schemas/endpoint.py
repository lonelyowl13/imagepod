from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.schemas.template import TemplateResponse


class ExecutorResponse(BaseModel):
    """Executor object for endpoint responses"""
    id: int
    name: Optional[str] = None
    gpu_type: Optional[str] = None
    gpu_count: int = 1
    cuda_version: Optional[str] = None
    compute_type: str = "GPU"
    is_active: bool = True

    class Config:
        from_attributes = True


class EndpointCreate(BaseModel):
    compute_type: str = Field("GPU")
    executor_id: int = Field(...)
    execution_timeout_ms: int = Field(600000)
    idle_timeout: int = Field(5)
    name: str
    template_id: int = Field(...)
    vcpu_count: int = Field(2)


class EndpointUpdate(BaseModel):
    version: Optional[int] = None
    compute_type: Optional[str] = None
    executor_id: Optional[int] = None
    execution_timeout_ms: Optional[int] = None
    idle_timeout: Optional[int] = None
    name: Optional[str] = None
    template_id: Optional[int] = None
    vcpu_count: Optional[int] = None
    env: Optional[Dict[str, Any]] = None


class EndpointResponse(BaseModel):
    id: int
    name: str
    compute_type: str = Field(...)
    executor_id: int = Field(...)
    execution_timeout_ms: int = Field(...)
    idle_timeout: int = Field(...)
    template_id: int = Field(...)
    vcpu_count: int = Field(...)
    env: Dict[str, str] = Field(default_factory=dict)
    version: int = 0
    status: str = Field(...)  # Deploying | Ready | Unhealthy
    created_at: datetime = Field(...)
    template: TemplateResponse
    executor: ExecutorResponse
    user_id: int = Field(...)

    class Config:
        from_attributes = True
