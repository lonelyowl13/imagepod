from pydantic import BaseModel
from typing import Optional, Dict, Any


class JobRunRequest(BaseModel):
    """Request body for POST /jobs/{id}/run"""
    input: Dict[str, Any]


class JobRunResponse(BaseModel):
    """Response for POST /jobs/{id}/run"""
    id: int
    status: str  # "IN_QUEUE"


class JobResponse(BaseModel):
    """Job object per jobs.txt"""
    id: int
    delay_time: int
    execution_time: int
    output: Optional[Dict[str, Any]] = None
    input: Dict[str, Any]
    status: str  # IN_QUEUE | RUNNING | COMPLETED | FAILED | CANCELLED | TIMED_OUT
    endpoint_id: int
    executor_id: int

    class Config:
        from_attributes = True


class JobStatusUpdate(BaseModel):
    """Used by external workers to update job status"""
    status: str
    output_data: Optional[Dict[str, Any]] = None
    execution_time: Optional[int] = None  # milliseconds
