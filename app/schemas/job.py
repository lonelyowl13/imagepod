from pydantic import BaseModel
from typing import Optional, Dict, Any


class JobRunRequest(BaseModel):
    """Request body for POST /jobs/{endpoint_id}/run"""
    input: Dict[str, Any]


class JobRunResponse(BaseModel):
    """Response for POST /jobs/{endpoint_id}/run"""
    id: str  # UUID as string
    status: str  # "IN_QUEUE"


class JobResponse(BaseModel):
    """Full job response"""
    id: str  # UUID as string
    delay_time: int
    execution_time: int
    output: Optional[Dict[str, Any]] = None
    input: Dict[str, Any]
    status: str  # IN_QUEUE | RUNNING | COMPLETED | FAILED | CANCELLED | TIMED_OUT
    endpoint_id: Optional[int] = None

    class Config:
        from_attributes = True


class JobStatusUpdate(BaseModel):
    """Used by external workers to update job status"""
    status: str
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    gpu_memory_used: Optional[int] = None
    cpu_cores_used: Optional[int] = None
    ram_used: Optional[int] = None
    duration_seconds: Optional[float] = None
