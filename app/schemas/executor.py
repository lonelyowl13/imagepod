from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from pydantic import BaseModel

EndpointStatus = Literal["DEPLOYING", "READY", "UNHEALTHY"]

from app.schemas.template import TemplateResponse
from app.schemas.job import JobResponse


class ExecutorAddRequest(BaseModel):
    name: str


class ExecutorAddResponse(BaseModel):
    api_key: str
    executor_id: int


class ExecutorRegisterRequest(BaseModel):
    gpu: Optional[str] = None
    vram: Optional[int] = None  # bytes
    cpu: Optional[str] = None
    ram: Optional[int] = None  # bytes
    compute_type: Optional[str] = None
    cuda_version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ExecutorJobUpdateRequest(BaseModel):
    delay_time: Optional[int] = None
    execution_time: Optional[int] = None
    output_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class EndpointStatusUpdate(BaseModel):
    """Executor-only: set endpoint status (READY, UNHEALTHY, DEPLOYING)"""
    status: EndpointStatus


class ExecutorSummary(BaseModel):
    id: int
    name: Optional[str] = None
    compute_type: Optional[str] = None
    is_active: bool
    created_at: datetime
    gpu: Optional[str] = None
    cpu: Optional[str] = None
    ram: Optional[int] = None  # bytes
    vram: Optional[int] = None  # bytes
    last_heartbeat: Optional[datetime] = None

    class Config:
        from_attributes = True


class EndpointUpdateItem(BaseModel):
    """Endpoint summary for executor updates (e.g. status=Deploying)."""
    id: int
    name: str
    status: str
    template_id: int
    executor_id: int
    template: TemplateResponse
    env: Dict[str, Any]
    version: int

    class Config:
        from_attributes = True


class ExecutorUpdatesResponse(BaseModel):
    """Unified response for GET /executors/updates: jobs IN_QUEUE + endpoints with status Deploying."""
    jobs: List[JobResponse]
    endpoints: List[EndpointUpdateItem]
