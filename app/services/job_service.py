from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.job import Job
from app.models.endpoint import Endpoint
from app.schemas.job import JobStatusUpdate
import uuid
from datetime import datetime


class JobService:
    def __init__(self, db: Session):
        self.db = db

    def create_job_for_endpoint(self, endpoint_id: str, user_id: int, input_data: Dict[str, Any]) -> Job:
        """Create a job for a specific endpoint"""
        # Get endpoint by endpoint_id (string)
        endpoint = self.db.query(Endpoint).filter(Endpoint.endpoint_id == endpoint_id).first()
        if not endpoint:
            raise ValueError("Endpoint not found")
        
        # Verify user owns the endpoint
        if endpoint.user_id != user_id:
            raise ValueError("Endpoint not found")  # Don't reveal it exists but belongs to another user
        
        # Create job
        db_job = Job(
            id=uuid.uuid4(),
            user_id=user_id,
            endpoint_id=endpoint.id,  # Use internal integer ID
            input_data=input_data,
            status="IN_QUEUE",
            delay_time=0,
            execution_time=0
        )

        self.db.add(db_job)
        self.db.commit()
        self.db.refresh(db_job)

        return db_job

    def get_job(self, job_id: str, user_id: Optional[int] = None) -> Optional[Job]:
        """Get job by UUID (string)"""
        try:
            job_uuid = uuid.UUID(job_id)
        except ValueError:
            return None
        
        query = self.db.query(Job).filter(Job.id == job_uuid)
        if user_id:
            query = query.filter(Job.user_id == user_id)
        return query.first()

    def get_job_by_endpoint(self, endpoint_id: str, job_id: str, user_id: Optional[int] = None) -> Optional[Job]:
        """Get job by endpoint_id and job_id"""
        # Get endpoint by endpoint_id (string)
        endpoint = self.db.query(Endpoint).filter(Endpoint.endpoint_id == endpoint_id).first()
        if not endpoint:
            return None
        
        # Verify user owns the endpoint if user_id provided
        if user_id and endpoint.user_id != user_id:
            return None
        
        job = self.get_job(job_id, user_id)
        if not job or job.endpoint_id != endpoint.id:
            return None
        
        return job

    def cancel_job(self, job_id: str, user_id: Optional[int] = None) -> Optional[Job]:
        """Cancel a job"""
        job = self.get_job(job_id, user_id)
        if not job:
            return None
        
        # Only cancel if job is still queued or running
        if job.status in ["IN_QUEUE", "RUNNING"]:
            job.status = "CANCELLED"
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
            
            self.db.commit()
            self.db.refresh(job)
        
        return job

    def update_job_status(self, job_id: str, status_update: JobStatusUpdate) -> Optional[Job]:
        """Update job status (used by external workers)"""
        job = self.get_job(job_id)
        if not job:
            return None

        # Update status and related fields
        if status_update.status:
            job.status = status_update.status
            
            if status_update.status == "RUNNING" and not job.started_at:
                job.started_at = datetime.utcnow()
            elif status_update.status in ["COMPLETED", "FAILED", "CANCELLED"] and not job.completed_at:
                job.completed_at = datetime.utcnow()
                if job.started_at:
                    job.duration_seconds = (job.completed_at - job.started_at).total_seconds()

        if status_update.output_data is not None:
            job.output_data = status_update.output_data

        if status_update.error_message is not None:
            job.error_message = status_update.error_message

        if status_update.gpu_memory_used is not None:
            job.gpu_memory_used = status_update.gpu_memory_used

        if status_update.cpu_cores_used is not None:
            job.cpu_cores_used = status_update.cpu_cores_used

        if status_update.ram_used is not None:
            job.ram_used = status_update.ram_used

        if status_update.duration_seconds is not None:
            job.duration_seconds = status_update.duration_seconds
            job.execution_time = int(status_update.duration_seconds * 1000)  # Convert to milliseconds

        self.db.commit()
        self.db.refresh(job)
        return job
