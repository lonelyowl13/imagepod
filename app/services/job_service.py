from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.job import Job
from app.models.endpoint import Endpoint
from app.schemas.job import JobStatusUpdate


def create_job_for_endpoint(
    db: Session, endpoint_id: int, user_id: int, input_data: Dict[str, Any]
) -> Job:
    endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    if not endpoint:
        raise ValueError("Endpoint not found")
    if endpoint.user_id != user_id:
        raise ValueError("Endpoint not found")
    job = Job(
        input_data=input_data,
        status="IN_QUEUE",
        delay_time=0,
        execution_time=0,
        endpoint_id=endpoint.id,
        executor_id=endpoint.executor_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: int) -> Optional[Job]:
    return db.query(Job).filter(Job.id == job_id).first()


def get_job_by_endpoint(
    db: Session, endpoint_id: int, job_id: int, user_id: Optional[int] = None
) -> Optional[Job]:
    endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    if not endpoint:
        return None
    if user_id is not None and endpoint.user_id != user_id:
        return None
    job = get_job(db, job_id)
    if not job or job.endpoint_id != endpoint.id:
        return None
    return job


def cancel_job(db: Session, job_id: int, user_id: Optional[int] = None) -> Optional[Job]:
    job = get_job(db, job_id)
    if not job:
        return None
    if job.status in ("IN_QUEUE", "RUNNING"):
        job.status = "CANCELLED"
        db.commit()
        db.refresh(job)
    return job


def update_job_status(
    db: Session, job_id: int, status_update: JobStatusUpdate
) -> Optional[Job]:
    job = get_job(db, job_id)
    if not job:
        return None
    if status_update.status:
        job.status = status_update.status
    if status_update.output_data is not None:
        job.output_data = status_update.output_data
    if status_update.execution_time is not None:
        job.execution_time = status_update.execution_time
    db.commit()
    db.refresh(job)
    return job
