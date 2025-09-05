from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class JobTemplate(Base):
    __tablename__ = "job_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    docker_image = Column(String, nullable=False)
    docker_tag = Column(String, default="latest")
    
    # Template configuration
    template_config = Column(JSON)  # RunPod serverless template config
    input_schema = Column(JSON)  # JSON schema for input validation
    output_schema = Column(JSON)  # JSON schema for output validation
    
    # Resource requirements
    min_gpu_memory = Column(Integer)  # MB
    max_gpu_memory = Column(Integer)  # MB
    min_cpu_cores = Column(Integer)
    max_cpu_cores = Column(Integer)
    min_ram = Column(Integer)  # MB
    max_ram = Column(Integer)  # MB
    
    # Pricing
    base_price_per_second = Column(Float, default=0.0)
    
    # Metadata
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="created_templates")
    jobs = relationship("Job", back_populates="template")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("job_templates.id"))
    
    # Job identification
    name = Column(String)
    description = Column(Text)
    
    # Job status
    status = Column(String, default="pending")  # pending, running, completed, failed, cancelled
    
    # Input/Output
    input_data = Column(JSON)
    output_data = Column(JSON)
    error_message = Column(Text)
    
    # Worker assignment
    worker_id = Column(Integer, ForeignKey("workers.id"))
    worker_pool_id = Column(Integer, ForeignKey("worker_pools.id"))
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"))
    
    # Resource usage
    gpu_memory_used = Column(Integer)  # MB
    cpu_cores_used = Column(Integer)
    ram_used = Column(Integer)  # MB
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Float)
    
    # Billing
    cost = Column(Float, default=0.0)
    billing_account_id = Column(Integer, ForeignKey("billing_accounts.id"))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="jobs")
    template = relationship("JobTemplate", back_populates="jobs")
    worker = relationship("Worker", back_populates="jobs")
    worker_pool = relationship("WorkerPool", back_populates="jobs")
    billing_account = relationship("BillingAccount", back_populates="jobs")
    endpoint = relationship("Endpoint", back_populates="jobs")
