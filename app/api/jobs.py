from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_active_user
from app.models.user import User
from app.schemas.job import JobResponse, JobRunRequest, JobRunResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/{endpoint_id}/run", response_model=JobRunResponse, status_code=status.HTTP_200_OK)
async def run_job(
    endpoint_id: str,
    job_request: JobRunRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Submit a job to an endpoint"""
    job_service = JobService(db)
    
    try:
        job = job_service.create_job_for_endpoint(endpoint_id, current_user.id, job_request.input)
        return JobRunResponse(
            id=str(job.id),
            status="IN_QUEUE"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")


@router.get("/{endpoint_id}/status/{job_id}", response_model=JobResponse)
async def get_job_status(
    endpoint_id: str,
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get job status"""
    job_service = JobService(db)
    job = job_service.get_job_by_endpoint(endpoint_id, job_id, current_user.id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(
        id=str(job.id),
        delay_time=job.delay_time,
        execution_time=job.execution_time,
        output=job.output_data,
        input=job.input_data,
        status=job.status,
        endpoint_id=job.endpoint_id
    )


@router.get("/{endpoint_id}/cancel/{job_id}", response_model=JobResponse)
async def cancel_job(
    endpoint_id: str,
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a job"""
    job_service = JobService(db)
    
    # Verify endpoint exists and user owns it
    job = job_service.get_job_by_endpoint(endpoint_id, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Cancel the job
    cancelled_job = job_service.cancel_job(job_id, current_user.id)
    if not cancelled_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(
        id=str(cancelled_job.id),
        delay_time=cancelled_job.delay_time,
        execution_time=cancelled_job.execution_time,
        output=cancelled_job.output_data,
        input=cancelled_job.input_data,
        status=cancelled_job.status,
        endpoint_id=cancelled_job.endpoint_id
    )
