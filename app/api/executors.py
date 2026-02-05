from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.helpers import get_current_executor, get_current_active_user
from app.models.executor import Executor
from app.models.user import User
from app.schemas.executor import (
    ExecutorAddRequest,
    ExecutorAddResponse,
    ExecutorRegisterRequest,
    ExecutorJobUpdateRequest,
    ExecutorSummary,
)
from app.schemas.job import JobResponse
from app.services.executor_service import (
    create_executor_with_key,
    update_executor_spec,
    get_jobs_in_queue,
    update_job_for_executor,
    get_endpoints_for_executor,
    get_executors_for_user,
)

router = APIRouter(prefix="/executors", tags=["executors"])


@router.post("/add", response_model=ExecutorAddResponse)
def add_executor(
    body: ExecutorAddRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add an executor to the database. Returns API key and executor_id."""
    result = create_executor_with_key(db, current_user.id, body.name)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create executor")
    executor, raw_key = result
    return ExecutorAddResponse(api_key=raw_key, executor_id=executor.id)


@router.post("/register")
def register_executor(
    body: ExecutorRegisterRequest,
    executor: Executor = Depends(get_current_executor),
    db: Session = Depends(get_db),
):
    """Register executor specs (called by the executor with its API key)."""
    updated = update_executor_spec(
        db,
        executor.id,
        gpu=body.gpu,
        vram=body.vram,
        cpu=body.cpu,
        ram=body.ram,
        compute_type=body.compute_type,
        cuda_version=body.cuda_version,
        metadata=body.metadata,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Executor not found")
    return {"detail": "ok", "executor_id": executor.id}


@router.get("/jobs", response_model=List[JobResponse])
def list_executor_jobs(
    executor: Executor = Depends(get_current_executor),
    db: Session = Depends(get_db),
):
    """Return all jobs for this executor with status IN_QUEUE."""
    jobs = get_jobs_in_queue(db, executor.id)
    return [
        JobResponse(
            id=j.id,
            delay_time=j.delay_time,
            execution_time=j.execution_time,
            output=j.output_data,
            input=j.input_data,
            status=j.status,
            endpoint_id=j.endpoint_id,
            executor_id=j.executor_id,
        )
        for j in jobs
    ]


@router.patch("/job/{job_id}")
def update_job(
    job_id: int,
    body: ExecutorJobUpdateRequest,
    executor: Executor = Depends(get_current_executor),
    db: Session = Depends(get_db),
):
    """Update job status (executor only; job must belong to this executor)."""
    job = update_job_for_executor(
        db,
        executor.id,
        job_id,
        status=body.status,
        delay_time=body.delay_time,
        execution_time=body.execution_time,
        output_data=body.output_data,
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"detail": "ok", "id": job.id}


@router.get("/", response_model=List[ExecutorSummary])
def list_user_executors(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all executors owned by the current user."""
    executors = get_executors_for_user(db, current_user.id)
    return executors


@router.get("/endpoints")
def list_executor_endpoints(
    executor: Executor = Depends(get_current_executor),
    db: Session = Depends(get_db),
):
    """Return all endpoints deployed on this executor."""
    endpoints = get_endpoints_for_executor(db, executor.id)
    return [
        {
            "id": e.id,
            "name": e.name,
            "template_id": e.template_id,
            "executor_id": e.executor_id,
        }
        for e in endpoints
    ]
