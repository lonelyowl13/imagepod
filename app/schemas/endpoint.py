from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class EndpointBase(BaseModel):
    name: str
    description: Optional[str] = None
    docker_image: str
    docker_tag: str = "latest"
    docker_registry: Optional[str] = None
    endpoint_config: Optional[Dict[str, Any]] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    min_gpu_memory: Optional[int] = None
    max_gpu_memory: Optional[int] = None
    min_cpu_cores: Optional[int] = None
    max_cpu_cores: Optional[int] = None
    min_ram: Optional[int] = None
    max_ram: Optional[int] = None
    min_replicas: int = 0
    max_replicas: int = 10
    target_replicas: int = 1
    auto_scaling: bool = True
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.2
    base_price_per_second: float = 0.0
    deployment_type: str = "kubernetes"
    deployment_config: Optional[Dict[str, Any]] = None
    is_public: bool = False
    api_key_required: bool = True
    rate_limit: Optional[int] = None


class EndpointCreate(EndpointBase):
    endpoint_id: Optional[str] = None  # If not provided, will be auto-generated


class EndpointUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    docker_image: Optional[str] = None
    docker_tag: Optional[str] = None
    endpoint_config: Optional[Dict[str, Any]] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    min_gpu_memory: Optional[int] = None
    max_gpu_memory: Optional[int] = None
    min_cpu_cores: Optional[int] = None
    max_cpu_cores: Optional[int] = None
    min_ram: Optional[int] = None
    max_ram: Optional[int] = None
    min_replicas: Optional[int] = None
    max_replicas: Optional[int] = None
    target_replicas: Optional[int] = None
    auto_scaling: Optional[bool] = None
    scale_up_threshold: Optional[float] = None
    scale_down_threshold: Optional[float] = None
    base_price_per_second: Optional[float] = None
    deployment_type: Optional[str] = None
    deployment_config: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    api_key_required: Optional[bool] = None
    rate_limit: Optional[int] = None


class EndpointResponse(EndpointBase):
    id: int
    user_id: int
    endpoint_id: str
    status: str
    health_status: str
    last_health_check: Optional[datetime] = None
    current_replicas: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_execution_time: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


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
    cost: float
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
