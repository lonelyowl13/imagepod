from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Endpoint identification
    endpoint_id = Column(String, unique=True, index=True)  # Custom endpoint ID (e.g., "jpnw0v75y3qoql")
    name = Column(String, nullable=False)
    
    # Template reference
    template_id = Column(String, ForeignKey("templates.template_id"), nullable=False)
    
    # Executor reference
    executor_id = Column(Integer, ForeignKey("executors.id"), nullable=False)
    
    # Configuration
    allowed_cuda_versions = Column(JSON)  # Array of strings like ["12.9"]
    compute_type = Column(String, default="GPU")  # GPU, CPU, etc.
    execution_timeout_ms = Column(Integer, default=600000)  # milliseconds
    idle_timeout = Column(Integer, default=5)  # minutes
    vcpu_count = Column(Integer, default=2)
    
    # Environment variables (can override template env)
    env = Column(JSON)  # Dictionary of env vars
    
    # Version tracking
    version = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="endpoints")
    template = relationship("Template", foreign_keys=[template_id], primaryjoin="Endpoint.template_id == Template.template_id")
    executor = relationship("Executor", back_populates="endpoints")
    jobs = relationship("Job", back_populates="endpoint")
    deployments = relationship("EndpointDeployment", back_populates="endpoint")


class EndpointDeployment(Base):
    __tablename__ = "endpoint_deployments"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
    
    # Deployment identification
    deployment_id = Column(String, unique=True, index=True)
    version = Column(String, default="1.0.0")
    
    # Deployment status
    status = Column(String, default="pending")  # pending, deploying, active, failed, terminated
    health_status = Column(String, default="unknown")
    
    # Resource usage
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    gpu_usage = Column(Float, default=0.0)
    
    # Infrastructure details
    node_name = Column(String)
    pod_name = Column(String)
    container_id = Column(String)
    instance_id = Column(String)
    
    # Deployment metadata
    deployment_metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    terminated_at = Column(DateTime(timezone=True))
    last_heartbeat = Column(DateTime(timezone=True))
    
    # Relationships
    endpoint = relationship("Endpoint", back_populates="deployments")
