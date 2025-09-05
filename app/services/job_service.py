from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.job import Job, JobTemplate
from app.models.worker import Worker, WorkerPool
from app.schemas.job import JobCreate, JobUpdate, JobTemplateCreate, JobStatusUpdate
from app.services.worker_service import WorkerService
from app.services.billing_service import BillingService
import json
import uuid
from datetime import datetime


class JobService:
    def __init__(self, db: Session):
        self.db = db
        self.worker_service = WorkerService(db)
        self.billing_service = BillingService(db)

    def create_job(self, user_id: int, job_data: JobCreate) -> Job:
        # Validate template if provided
        template = None
        if job_data.template_id:
            template = self.get_template(job_data.template_id)
            if not template:
                raise ValueError("Template not found")
            if not template.is_active:
                raise ValueError("Template is not active")

        # Create job
        db_job = Job(
            user_id=user_id,
            template_id=job_data.template_id,
            name=job_data.name,
            description=job_data.description,
            input_data=job_data.input_data,
            status="pending"
        )

        self.db.add(db_job)
        self.db.commit()
        self.db.refresh(db_job)

        # Try to assign worker
        self._assign_worker(db_job)

        return db_job

    def get_job(self, job_id: int, user_id: Optional[int] = None) -> Optional[Job]:
        query = self.db.query(Job).filter(Job.id == job_id)
        if user_id:
            query = query.filter(Job.user_id == user_id)
        return query.first()

    def get_user_jobs(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Job]:
        return (
            self.db.query(Job)
            .filter(Job.user_id == user_id)
            .order_by(desc(Job.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_jobs(self, skip: int = 0, limit: int = 100) -> List[Job]:
        return (
            self.db.query(Job)
            .order_by(desc(Job.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_job(self, job_id: int, job_update: JobUpdate, user_id: Optional[int] = None) -> Optional[Job]:
        job = self.get_job(job_id, user_id)
        if not job:
            return None

        update_data = job_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)

        self.db.commit()
        self.db.refresh(job)
        return job

    def update_job_status(self, job_id: int, status_update: JobStatusUpdate) -> Optional[Job]:
        job = self.get_job(job_id)
        if not job:
            return None

        # Update status and related fields
        if status_update.status:
            job.status = status_update.status
            
            if status_update.status == "running" and not job.started_at:
                job.started_at = datetime.utcnow()
            elif status_update.status in ["completed", "failed", "cancelled"] and not job.completed_at:
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

        # Calculate cost if job is completed
        if job.status == "completed" and job.duration_seconds:
            job.cost = self._calculate_job_cost(job)

        self.db.commit()
        self.db.refresh(job)
        return job

    def delete_job(self, job_id: int, user_id: Optional[int] = None) -> bool:
        job = self.get_job(job_id, user_id)
        if not job:
            return False

        # Cancel job if it's still running
        if job.status in ["pending", "running"]:
            job.status = "cancelled"
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.duration_seconds = (job.completed_at - job.started_at).total_seconds()

        self.db.delete(job)
        self.db.commit()
        return True

    def create_template(self, user_id: int, template_data: JobTemplateCreate) -> JobTemplate:
        db_template = JobTemplate(
            created_by=user_id,
            **template_data.dict()
        )

        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        return db_template

    def get_template(self, template_id: int) -> Optional[JobTemplate]:
        return self.db.query(JobTemplate).filter(JobTemplate.id == template_id).first()

    def get_public_templates(self, skip: int = 0, limit: int = 100) -> List[JobTemplate]:
        return (
            self.db.query(JobTemplate)
            .filter(JobTemplate.is_public == True, JobTemplate.is_active == True)
            .order_by(desc(JobTemplate.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_user_templates(self, user_id: int, skip: int = 0, limit: int = 100) -> List[JobTemplate]:
        return (
            self.db.query(JobTemplate)
            .filter(JobTemplate.created_by == user_id)
            .order_by(desc(JobTemplate.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def _assign_worker(self, job: Job) -> bool:
        """Assign an available worker to the job"""
        # Find available worker based on job requirements
        available_worker = self.worker_service.find_available_worker(job)
        
        if available_worker:
            job.worker_id = available_worker.id
            job.worker_pool_id = available_worker.pool_id
            job.status = "running"
            job.started_at = datetime.utcnow()
            
            # Update worker status
            available_worker.status = "running"
            
            self.db.commit()
            return True
        
        return False

    def _calculate_job_cost(self, job: Job) -> float:
        """Calculate the cost of a completed job"""
        if not job.duration_seconds or not job.template:
            return 0.0

        # Base cost from template
        base_cost = job.template.base_price_per_second * job.duration_seconds

        # Add resource costs
        resource_cost = 0.0
        if job.gpu_memory_used:
            # GPU memory cost (example: $0.01 per GB-second)
            gpu_cost = (job.gpu_memory_used / 1024) * job.duration_seconds * 0.01
            resource_cost += gpu_cost

        if job.cpu_cores_used:
            # CPU cost (example: $0.001 per core-second)
            cpu_cost = job.cpu_cores_used * job.duration_seconds * 0.001
            resource_cost += cpu_cost

        if job.ram_used:
            # RAM cost (example: $0.0001 per MB-second)
            ram_cost = job.ram_used * job.duration_seconds * 0.0001
            resource_cost += ram_cost

        return base_cost + resource_cost

    def get_runpod_compatible_response(self, job: Job) -> Dict[str, Any]:
        """Convert job to RunPod serverless compatible response format"""
        return {
            "id": str(job.id),
            "status": job.status,
            "input": job.input_data,
            "output": job.output_data,
            "error": job.error_message,
            "executionTime": job.duration_seconds,
            "cost": job.cost,
            "createdAt": job.created_at.isoformat() if job.created_at else None,
            "startedAt": job.started_at.isoformat() if job.started_at else None,
            "completedAt": job.completed_at.isoformat() if job.completed_at else None,
        }
