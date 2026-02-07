from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.helpers import get_current_active_user
from app.models.user import User
from app.schemas.job import JobResponse, JobRunRequest, JobRunResponse
from app.services.job_service import (
    create_job_for_endpoint,
    get_job_by_endpoint,
    cancel_job,
)
from app.rabbitmq import publish_job_notification

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/{endpoint_id}/run", response_model=JobRunResponse, status_code=status.HTTP_200_OK)
async def run_job(
    request: Request,
    endpoint_id: int,
    job_request: JobRunRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Submit a job to an endpoint"""
    try:
        job = create_job_for_endpoint(db, endpoint_id, current_user.id, job_request.input)
        conn = getattr(request.app.state, "rabbitmq", None)
        if conn:
            await publish_job_notification(conn, job.executor_id)
        return JobRunResponse(id=job.id, status="IN_QUEUE")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{endpoint_id}/status/{job_id}", response_model=JobResponse)
async def get_job_status(
    endpoint_id: int,
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get job status"""
    job = get_job_by_endpoint(db, endpoint_id, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        id=job.id,
        delay_time=job.delay_time,
        execution_time=job.execution_time,
        output=job.output_data,
        input=job.input_data,
        status=job.status,
        endpoint_id=job.endpoint_id,
        executor_id=job.executor_id,
    )


@router.get("/{endpoint_id}/cancel/{job_id}", response_model=JobResponse)
async def cancel_job_route(
    endpoint_id: int,
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Cancel a job"""
    job = get_job_by_endpoint(db, endpoint_id, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    cancelled = cancel_job(db, job_id, current_user.id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        id=cancelled.id,
        delay_time=cancelled.delay_time,
        execution_time=cancelled.execution_time,
        output=cancelled.output_data,
        input=cancelled.input_data,
        status=cancelled.status,
        endpoint_id=cancelled.endpoint_id,
        executor_id=cancelled.executor_id,
    )
