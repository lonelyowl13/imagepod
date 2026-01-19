from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Endpoint identification
    name = Column(String, nullable=False)
    description = Column(Text)
    endpoint_id = Column(String, unique=True, index=True)  # Custom endpoint ID for URL routing
    
    # Docker configuration
    docker_image = Column(String, nullable=False)
    docker_tag = Column(String, default="latest")
    docker_registry = Column(String)  # Custom registry URL
    docker_username = Column(String)  # Registry username
    docker_password = Column(String)  # Registry password (encrypted)
    
    # Endpoint configuration
    endpoint_config = Column(JSON)  # Custom configuration for the endpoint
    input_schema = Column(JSON)  # JSON schema for input validation
    output_schema = Column(JSON)  # JSON schema for output validation
    
    # Resource requirements
    min_gpu_memory = Column(Integer)  # MB
    max_gpu_memory = Column(Integer)  # MB
    min_cpu_cores = Column(Integer)
    max_cpu_cores = Column(Integer)
    min_ram = Column(Integer)  # MB
    max_ram = Column(Integer)  # MB
    
    # Scaling configuration
    min_replicas = Column(Integer, default=0)
    max_replicas = Column(Integer, default=10)
    target_replicas = Column(Integer, default=1)
    auto_scaling = Column(Boolean, default=True)
    scale_up_threshold = Column(Float, default=0.8)
    scale_down_threshold = Column(Float, default=0.2)
    
    # Status and health
    status = Column(String, default="pending")  # pending, active, inactive, error
    health_status = Column(String, default="unknown")  # healthy, unhealthy, unknown
    last_health_check = Column(DateTime(timezone=True))
    
    # Deployment info
    deployment_type = Column(String, default="kubernetes")  # kubernetes, docker, serverless
    deployment_config = Column(JSON)
    current_replicas = Column(Integer, default=0)
    
    # Access control
    is_public = Column(Boolean, default=False)
    api_key_required = Column(Boolean, default=True)
    rate_limit = Column(Integer)  # requests per minute
    
    # Usage statistics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    total_execution_time = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deployed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="endpoints")
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
