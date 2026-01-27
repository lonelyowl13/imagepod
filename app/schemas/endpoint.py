from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.schemas.template import TemplateResponse


class ExecutorResponse(BaseModel):
    """Minimal executor response for endpoint responses"""
    id: str  # executor_id
    name: Optional[str] = None
    gpu_type: Optional[str] = None
    gpu_count: int = 1
    cuda_version: Optional[str] = None
    compute_type: str = "GPU"
    is_active: bool = True
    is_online: bool = False

    class Config:
        from_attributes = True


class EndpointCreate(BaseModel):
    allowedCudaVersions: List[str] = Field(default_factory=list, alias="allowed_cuda_versions")
    computeType: str = Field("GPU", alias="compute_type")
    executorId: int = Field(..., alias="executor_id")
    executionTimeoutMs: int = Field(600000, alias="execution_timeout_ms")
    idleTimeout: int = Field(5, alias="idle_timeout")
    name: str
    templateId: str = Field(..., alias="template_id")
    vcpuCount: int = Field(2, alias="vcpu_count")

    class Config:
        populate_by_name = True


class EndpointUpdate(BaseModel):
    allowedCudaVersions: Optional[List[str]] = Field(None, alias="allowed_cuda_versions")
    computeType: Optional[str] = Field(None, alias="compute_type")
    executorId: Optional[int] = Field(None, alias="executor_id")
    executionTimeoutMs: Optional[int] = Field(None, alias="execution_timeout_ms")
    idleTimeout: Optional[int] = Field(None, alias="idle_timeout")
    name: Optional[str] = None
    templateId: Optional[str] = Field(None, alias="template_id")
    vcpuCount: Optional[int] = Field(None, alias="vcpu_count")

    class Config:
        populate_by_name = True


class EndpointResponse(BaseModel):
    id: str  # endpoint_id
    name: str
    allowedCudaVersions: List[str] = Field(default_factory=list, alias="allowed_cuda_versions")
    computeType: str = Field(..., alias="compute_type")
    executorId: str = Field(..., alias="executor_id")  # String representation
    executionTimeoutMs: int = Field(..., alias="execution_timeout_ms")
    idleTimeout: int = Field(..., alias="idle_timeout")
    templateId: str = Field(..., alias="template_id")
    vcpuCount: int = Field(..., alias="vcpu_count")
    env: Dict[str, str] = Field(default_factory=dict)
    version: int = 0
    createdAt: datetime = Field(..., alias="created_at")
    template: TemplateResponse
    executor: ExecutorResponse
    userId: str = Field(..., alias="user_id")  # String representation

    class Config:
        from_attributes = True
        populate_by_name = True


# Keep old schemas for backward compatibility (if needed elsewhere)
class EndpointDeploymentResponse(BaseModel):
    id: int
    endpoint_id: int
    deployment_id: str
    version: str
    status: str
    health_status: str
    cpu_usage: float
    memory_usage: float
    gpu_usage: float
    node_name: Optional[str] = None
    pod_name: Optional[str] = None
    container_id: Optional[str] = None
    instance_id: Optional[str] = None
    deployment_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None

    class Config:
        from_attributes = True


class EndpointJobRequest(BaseModel):
    input: Dict[str, Any]
    timeout: Optional[int] = 300  # seconds
    priority: Optional[str] = "normal"  # low, normal, high


class EndpointJobResponse(BaseModel):
    id: str
    status: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    executionTime: Optional[float] = None
    createdAt: str
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None


class EndpointStatsResponse(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    average_execution_time: float
    total_execution_time: float
    current_replicas: int
    cpu_usage: float
    memory_usage: float
    gpu_usage: float


class DockerImageUpload(BaseModel):
    image_name: str
    image_tag: str = "latest"
    registry_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class EndpointScaleRequest(BaseModel):
    target_replicas: int = Field(..., ge=0, le=100)
