from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class GPUNodeBase(BaseModel):
    node_name: str
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    region: Optional[str] = None
    zone: Optional[str] = None
    cluster_name: str = "default"
    
    # GPU information
    gpu_count: int = 0
    gpu_type: Optional[str] = None
    gpu_memory_total: Optional[int] = None
    gpu_driver_version: Optional[str] = None
    gpu_cuda_version: Optional[str] = None
    
    # System resources
    cpu_cores: Optional[int] = None
    memory_total: Optional[int] = None
    storage_total: Optional[int] = None
    
    # Worker configuration
    max_concurrent_jobs: int = 1
    auto_register: bool = True
    
    # Pricing
    price_per_gpu_hour: float = 0.0
    price_per_cpu_hour: float = 0.0
    price_per_memory_gb_hour: float = 0.0
    
    # Kubernetes information
    k8s_node_name: Optional[str] = None
    k8s_cluster: Optional[str] = None
    k8s_namespace: str = "default"
    k8s_labels: Optional[Dict[str, str]] = None
    k8s_taints: Optional[List[Dict[str, Any]]] = None
    
    # Network
    api_endpoint: Optional[str] = None
    ssh_endpoint: Optional[str] = None
    vnc_endpoint: Optional[str] = None
    
    # Metadata
    node_metadata: Optional[Dict[str, Any]] = None


class GPUNodeRegistration(GPUNodeBase):
    """Schema for GPU node registration"""
    node_id: Optional[str] = None
    registration_token: Optional[str] = None


class GPUNodeUpdate(BaseModel):
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    gpu_count: Optional[int] = None
    gpu_memory_total: Optional[int] = None
    gpu_memory_available: Optional[int] = None
    cpu_cores: Optional[int] = None
    cpu_cores_available: Optional[int] = None
    memory_total: Optional[int] = None
    memory_available: Optional[int] = None
    storage_total: Optional[int] = None
    storage_available: Optional[int] = None
    status: Optional[str] = None
    health_status: Optional[str] = None
    current_jobs: Optional[int] = None
    max_concurrent_jobs: Optional[int] = None
    price_per_gpu_hour: Optional[float] = None
    price_per_cpu_hour: Optional[float] = None
    price_per_memory_gb_hour: Optional[float] = None
    api_endpoint: Optional[str] = None
    node_metadata: Optional[Dict[str, Any]] = None


class GPUNodeResponse(GPUNodeBase):
    id: int
    node_id: str
    gpu_memory_available: Optional[int] = None
    cpu_cores_available: Optional[int] = None
    memory_available: Optional[int] = None
    storage_available: Optional[int] = None
    status: str
    health_status: str
    last_heartbeat: Optional[datetime] = None
    current_jobs: int
    registered_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GPUInstanceResponse(BaseModel):
    id: int
    node_id: int
    gpu_index: int
    gpu_uuid: str
    gpu_name: Optional[str] = None
    gpu_type: Optional[str] = None
    gpu_memory: Optional[int] = None
    compute_capability: Optional[str] = None
    status: str
    current_job_id: Optional[int] = None
    utilization: float
    temperature: Optional[float] = None
    power_usage: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None

    class Config:
        from_attributes = True


class GPUJobBase(BaseModel):
    job_name: Optional[str] = None
    job_type: str = "gpu_inference"
    docker_image: str
    docker_tag: str = "latest"
    docker_registry: Optional[str] = None
    job_config: Optional[Dict[str, Any]] = None
    input_data: Optional[Dict[str, Any]] = None
    
    # Resource requirements
    gpu_memory_required: Optional[int] = None
    cpu_cores_required: Optional[int] = None
    memory_required: Optional[int] = None
    storage_required: Optional[int] = None


class GPUJobCreate(GPUJobBase):
    endpoint_id: Optional[int] = None


class GPUJobUpdate(BaseModel):
    status: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    gpu_memory_used: Optional[int] = None
    cpu_cores_used: Optional[int] = None
    memory_used: Optional[int] = None
    storage_used: Optional[int] = None
    duration_seconds: Optional[float] = None


class GPUJobResponse(GPUJobBase):
    id: int
    user_id: int
    endpoint_id: Optional[int] = None
    status: str
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    assigned_node_id: Optional[int] = None
    assigned_gpu_id: Optional[int] = None
    k8s_pod_name: Optional[str] = None
    k8s_deployment_name: Optional[str] = None
    k8s_job_name: Optional[str] = None
    gpu_memory_used: Optional[int] = None
    cpu_cores_used: Optional[int] = None
    memory_used: Optional[int] = None
    storage_used: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    cost: float
    billing_account_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkerAgentBase(BaseModel):
    agent_id: str
    agent_version: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    capabilities: Optional[Dict[str, Any]] = None
    api_endpoint: Optional[str] = None
    websocket_endpoint: Optional[str] = None


class WorkerAgentRegistration(WorkerAgentBase):
    """Schema for worker agent registration"""
    node_id: int
    registration_token: Optional[str] = None


class WorkerAgentUpdate(BaseModel):
    status: Optional[str] = None
    health_status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    capabilities: Optional[Dict[str, Any]] = None
    api_endpoint: Optional[str] = None
    websocket_endpoint: Optional[str] = None


class WorkerAgentResponse(WorkerAgentBase):
    id: int
    node_id: int
    status: str
    health_status: str
    last_heartbeat: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NodeHeartbeat(BaseModel):
    """Schema for node heartbeat updates"""
    node_id: str
    gpu_memory_available: Optional[int] = None
    cpu_cores_available: Optional[int] = None
    memory_available: Optional[int] = None
    storage_available: Optional[int] = None
    current_jobs: Optional[int] = None
    gpu_instances: Optional[List[Dict[str, Any]]] = None
    health_status: Optional[str] = None


class JobSubmission(BaseModel):
    """Schema for job submission to GPU nodes"""
    job_id: int
    docker_image: str
    docker_tag: str = "latest"
    docker_registry: Optional[str] = None
    docker_username: Optional[str] = None
    docker_password: Optional[str] = None
    job_config: Optional[Dict[str, Any]] = None
    input_data: Optional[Dict[str, Any]] = None
    resource_requirements: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = 3600  # seconds


class JobStatusUpdate(BaseModel):
    """Schema for job status updates from GPU nodes"""
    job_id: int
    status: str
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    resource_usage: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[float] = None


class NodeStats(BaseModel):
    """Schema for node statistics"""
    total_gpu_memory: int
    available_gpu_memory: int
    total_cpu_cores: int
    available_cpu_cores: int
    total_memory: int
    available_memory: int
    current_jobs: int
    max_concurrent_jobs: int
    utilization_percentage: float
    gpu_utilization: List[float]
    temperature: List[Optional[float]]
    power_usage: List[Optional[float]]
