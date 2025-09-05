from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class WorkerPoolBase(BaseModel):
    name: str
    description: Optional[str] = None
    min_workers: int = 0
    max_workers: int = 10
    target_workers: int = 1
    gpu_type: Optional[str] = None
    gpu_memory: Optional[int] = None
    cpu_cores: Optional[int] = None
    ram: Optional[int] = None
    storage: Optional[int] = None
    auto_scaling: bool = True
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.2
    scale_up_cooldown: int = 300
    scale_down_cooldown: int = 600
    infrastructure_type: str = "kubernetes"
    infrastructure_config: Optional[Dict[str, Any]] = None


class WorkerPoolCreate(WorkerPoolBase):
    pass


class WorkerPoolResponse(WorkerPoolBase):
    id: int
    is_active: bool
    current_workers: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkerBase(BaseModel):
    name: str
    pool_id: int
    gpu_type: Optional[str] = None
    gpu_memory: Optional[int] = None
    cpu_cores: Optional[int] = None
    ram: Optional[int] = None
    storage: Optional[int] = None
    endpoint_url: Optional[str] = None
    worker_metadata: Optional[Dict[str, Any]] = None


class WorkerCreate(WorkerBase):
    pass


class WorkerResponse(WorkerBase):
    id: int
    worker_id: str
    status: str
    health_status: str
    gpu_utilization: float
    cpu_utilization: float
    memory_utilization: float
    node_name: Optional[str] = None
    pod_name: Optional[str] = None
    container_id: Optional[str] = None
    instance_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    terminated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkerStatusUpdate(BaseModel):
    status: Optional[str] = None
    health_status: Optional[str] = None
    gpu_utilization: Optional[float] = None
    cpu_utilization: Optional[float] = None
    memory_utilization: Optional[float] = None
    last_heartbeat: Optional[datetime] = None
