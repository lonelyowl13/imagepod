from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class WorkerPool(Base):
    __tablename__ = "worker_pools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Pool configuration
    min_workers = Column(Integer, default=0)
    max_workers = Column(Integer, default=10)
    target_workers = Column(Integer, default=1)
    
    # Resource configuration
    gpu_type = Column(String)  # e.g., "RTX 4090", "A100"
    gpu_memory = Column(Integer)  # MB
    cpu_cores = Column(Integer)
    ram = Column(Integer)  # MB
    storage = Column(Integer)  # GB
    
    # Scaling configuration
    auto_scaling = Column(Boolean, default=True)
    scale_up_threshold = Column(Float, default=0.8)  # CPU/GPU utilization
    scale_down_threshold = Column(Float, default=0.2)
    scale_up_cooldown = Column(Integer, default=300)  # seconds
    scale_down_cooldown = Column(Integer, default=600)  # seconds
    
    # Infrastructure
    infrastructure_type = Column(String, default="kubernetes")  # kubernetes, docker, aws
    infrastructure_config = Column(JSON)
    
    # Status
    is_active = Column(Boolean, default=True)
    current_workers = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    workers = relationship("Worker", back_populates="pool")
    jobs = relationship("Job", back_populates="worker_pool")


class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("worker_pools.id"), nullable=False)
    
    # Worker identification
    name = Column(String, nullable=False)
    worker_id = Column(String, unique=True, index=True)  # External worker ID
    
    # Status
    status = Column(String, default="pending")  # pending, running, idle, error, terminated
    health_status = Column(String, default="unknown")  # healthy, unhealthy, unknown
    
    # Resource information
    gpu_type = Column(String)
    gpu_memory = Column(Integer)  # MB
    cpu_cores = Column(Integer)
    ram = Column(Integer)  # MB
    storage = Column(Integer)  # GB
    
    # Current usage
    gpu_utilization = Column(Float, default=0.0)
    cpu_utilization = Column(Float, default=0.0)
    memory_utilization = Column(Float, default=0.0)
    
    # Infrastructure details
    node_name = Column(String)  # Kubernetes node name
    pod_name = Column(String)  # Kubernetes pod name
    container_id = Column(String)  # Docker container ID
    instance_id = Column(String)  # AWS instance ID
    
    # Connection info
    endpoint_url = Column(String)
    api_key = Column(String)
    
    # Metadata
    worker_metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    last_heartbeat = Column(DateTime(timezone=True))
    terminated_at = Column(DateTime(timezone=True))
    
    # Relationships
    pool = relationship("WorkerPool", back_populates="workers")
    jobs = relationship("Job", back_populates="worker")
