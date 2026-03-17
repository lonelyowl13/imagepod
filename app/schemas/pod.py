from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field

from app.enums import PodStatus
from app.schemas.template import TemplateResponse
from app.schemas.endpoint import ExecutorResponse


class PodTunnelResponse(BaseModel):
    id: int
    port: int
    token: str
    domain: str
    created_at: datetime

    class Config:
        from_attributes = True


class PodCreate(BaseModel):
    compute_type: str = Field("GPU")
    executor_id: int = Field(...)
    name: str
    template_id: int = Field(...)
    vcpu_count: int = Field(2)
    ports: List[int] = Field(default_factory=list)
    env: Optional[Dict[str, Any]] = None


class PodUpdate(BaseModel):
    compute_type: Optional[str] = None
    executor_id: Optional[int] = None
    name: Optional[str] = None
    template_id: Optional[int] = None
    vcpu_count: Optional[int] = None
    ports: Optional[List[int]] = None
    env: Optional[Dict[str, Any]] = None


class PodResponse(BaseModel):
    id: int
    name: str
    compute_type: str
    executor_id: int
    template_id: int
    vcpu_count: int
    env: Dict[str, Any] = Field(default_factory=dict)
    ports: List[int] = Field(default_factory=list)
    status: PodStatus
    created_at: datetime
    last_started_at: Optional[datetime] = None
    last_stopped_at: Optional[datetime] = None
    template: TemplateResponse
    executor: ExecutorResponse
    user_id: int
    tunnels: List[PodTunnelResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

