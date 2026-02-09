from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.helpers import build_updates_response, get_current_executor, get_current_active_user
from app.models.executor import Executor
from app.models.user import User
from app.schemas.executor import (
    ExecutorAddRequest,
    ExecutorAddResponse,
    ExecutorRegisterRequest,
    ExecutorJobUpdateRequest,
    ExecutorSummary,
    ExecutorUpdatesResponse,
    EndpointStatusUpdate,
)
from app.services.executor_service import (
    create_executor_with_key,
    update_executor_spec,
    update_job_for_executor,
    get_endpoints_for_executor,
    get_executors_for_user,
)
from app.services.endpoint_service import update_endpoint_status_by_executor
from app.rabbitmq import wait_for_executor_notification

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


@router.get("/updates", response_model=ExecutorUpdatesResponse)
async def get_updates(
    request: Request,
    executor: Executor = Depends(get_current_executor),
    db: Session = Depends(get_db),
    timeout: float = 20.0,
):
    """
    Unified updates: jobs with status IN_QUEUE and endpoints with status Deploying.
    Long-poll: wait up to `timeout` seconds (max 60) for a notification (new job or endpoint), then return.
    If RabbitMQ is unavailable, returns immediately with current state.
    """
    wait_seconds = min(max(0.0, timeout), 60.0)
    conn = getattr(request.app.state, "rabbitmq", None)
    if conn and wait_seconds > 0:
        await wait_for_executor_notification(conn, executor.id, wait_seconds)
    return build_updates_response(db, executor.id)


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
            "status": getattr(e, "status", "DEPLOYING"),
            "template_id": e.template_id,
            "executor_id": e.executor_id,
        }
        for e in endpoints
    ]


@router.patch("/endpoints/{endpoint_id}")
def update_endpoint_status(
    endpoint_id: int,
    body: EndpointStatusUpdate,
    executor: Executor = Depends(get_current_executor),
    db: Session = Depends(get_db),
):
    """Update an endpoint's status (executor only; endpoint must belong to this executor)."""
    updated = update_endpoint_status_by_executor(db, endpoint_id, executor.id, body.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return {"detail": "ok", "id": updated.id, "status": updated.status}
