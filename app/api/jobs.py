from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.auth import get_current_active_user
from app.models.user import User
from app.schemas.job import JobCreate, JobUpdate, JobResponse, JobTemplateCreate, JobTemplateResponse, JobStatusUpdate
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobResponse)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new job"""
    job_service = JobService(db)
    
    try:
        job = job_service.create_job(current_user.id, job_data)
        return job
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[JobResponse])
async def get_user_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's jobs"""
    job_service = JobService(db)
    jobs = job_service.get_user_jobs(current_user.id, skip, limit)
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific job"""
    job_service = JobService(db)
    job = job_service.get_job(job_id, current_user.id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_update: JobUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a job"""
    job_service = JobService(db)
    job = job_service.update_job(job_id, job_update, current_user.id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a job"""
    job_service = JobService(db)
    success = job_service.delete_job(job_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": "Job deleted successfully"}


@router.get("/{job_id}/runpod")
async def get_job_runpod_format(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get job in RunPod serverless compatible format"""
    job_service = JobService(db)
    job = job_service.get_job(job_id, current_user.id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_service.get_runpod_compatible_response(job)


# Job Templates
@router.post("/templates/", response_model=JobTemplateResponse)
async def create_job_template(
    template_data: JobTemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new job template"""
    job_service = JobService(db)
    template = job_service.create_template(current_user.id, template_data)
    return template


@router.get("/templates/", response_model=List[JobTemplateResponse])
async def get_public_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get public job templates"""
    job_service = JobService(db)
    templates = job_service.get_public_templates(skip, limit)
    return templates


@router.get("/templates/my/", response_model=List[JobTemplateResponse])
async def get_user_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's job templates"""
    job_service = JobService(db)
    templates = job_service.get_user_templates(current_user.id, skip, limit)
    return templates


@router.get("/templates/{template_id}", response_model=JobTemplateResponse)
async def get_job_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific job template"""
    job_service = JobService(db)
    template = job_service.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template


# Admin endpoints for job status updates (used by workers)
@router.put("/{job_id}/status")
async def update_job_status(
    job_id: int,
    status_update: JobStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update job status (used by workers)"""
    job_service = JobService(db)
    job = job_service.update_job_status(job_id, status_update)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job
