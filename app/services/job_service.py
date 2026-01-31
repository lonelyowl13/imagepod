from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.job import Job
from app.models.endpoint import Endpoint
from app.schemas.job import JobStatusUpdate
import uuid


class JobService:
    def __init__(self, db: Session):
        self.db = db

    def create_job_for_endpoint(self, endpoint_id: str, user_id: int, input_data: Dict[str, Any]) -> Job:
        """Create a job for a specific endpoint"""
        endpoint = self.db.query(Endpoint).filter(Endpoint.endpoint_id == endpoint_id).first()
        if not endpoint:
            raise ValueError("Endpoint not found")
        if endpoint.user_id != user_id:
            raise ValueError("Endpoint not found")

        db_job = Job(
            id=uuid.uuid4(),
            input_data=input_data,
            status="IN_QUEUE",
            delay_time=0,
            execution_time=0,
            endpoint_id=endpoint.id,
            executor_id=endpoint.executor_id,
        )
        self.db.add(db_job)
        self.db.commit()
        self.db.refresh(db_job)
        return db_job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by UUID (string)"""
        try:
            job_uuid = uuid.UUID(job_id)
        except ValueError:
            return None
        return self.db.query(Job).filter(Job.id == job_uuid).first()

    def get_job_by_endpoint(self, endpoint_id: str, job_id: str, user_id: Optional[int] = None) -> Optional[Job]:
        """Get job by endpoint_id and job_id; optionally require user owns the endpoint"""
        endpoint = self.db.query(Endpoint).filter(Endpoint.endpoint_id == endpoint_id).first()
        if not endpoint:
            return None
        if user_id and endpoint.user_id != user_id:
            return None
        job = self.get_job(job_id)
        if not job or job.endpoint_id != endpoint.id:
            return None
        return job

    def cancel_job(self, job_id: str, user_id: Optional[int] = None) -> Optional[Job]:
        """Cancel a job (only if IN_QUEUE or RUNNING)"""
        job = self.get_job(job_id)
        if not job:
            return None
        if job.status in ("IN_QUEUE", "RUNNING"):
            job.status = "CANCELLED"
            self.db.commit()
            self.db.refresh(job)
        return job

    def update_job_status(self, job_id: str, status_update: JobStatusUpdate) -> Optional[Job]:
        """Update job status (used by external workers)"""
        job = self.get_job(job_id)
        if not job:
            return None
        if status_update.status:
            job.status = status_update.status
        if status_update.output_data is not None:
            job.output_data = status_update.output_data
        if status_update.execution_time is not None:
            job.execution_time = status_update.execution_time
        self.db.commit()
        self.db.refresh(job)
        return job
