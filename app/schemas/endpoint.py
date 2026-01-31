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
    computeType: str = Field("GPU", alias="compute_type")
    executorId: int = Field(..., alias="executor_id")
    executionTimeoutMs: int = Field(600000, alias="execution_timeout_ms")
    idleTimeout: int = Field(5, alias="idle_timeout")
    name: str
    templateId: int = Field(..., alias="template_id")
    vcpuCount: int = Field(2, alias="vcpu_count")

    class Config:
        populate_by_name = True


class EndpointUpdate(BaseModel):
    version: Optional[int] = None
    computeType: Optional[str] = Field(None, alias="compute_type")
    executorId: Optional[int] = Field(None, alias="executor_id")
    executionTimeoutMs: Optional[int] = Field(None, alias="execution_timeout_ms")
    idleTimeout: Optional[int] = Field(None, alias="idle_timeout")
    name: Optional[str] = None
    templateId: Optional[int] = Field(None, alias="template_id")
    vcpuCount: Optional[int] = Field(None, alias="vcpu_count")

    class Config:
        populate_by_name = True


class EndpointResponse(BaseModel):
    id: int
    name: str
    computeType: str = Field(..., alias="compute_type")
    executorId: int = Field(..., alias="executor_id")
    executionTimeoutMs: int = Field(..., alias="execution_timeout_ms")
    idleTimeout: int = Field(..., alias="idle_timeout")
    templateId: int = Field(..., alias="template_id")
    vcpuCount: int = Field(..., alias="vcpu_count")
    env: Dict[str, str] = Field(default_factory=dict)
    version: int = 0
    createdAt: datetime = Field(..., alias="created_at")
    template: TemplateResponse
    executor: ExecutorResponse
    userId: int = Field(..., alias="user_id")

    class Config:
        from_attributes = True
        populate_by_name = True
