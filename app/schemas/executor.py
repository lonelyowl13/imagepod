from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


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


class ExecutorSummary(BaseModel):
    id: int
    name: Optional[str] = None
    compute_type: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
