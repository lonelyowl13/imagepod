from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class GPUNode(Base):
    __tablename__ = "gpu_nodes"

    id = Column(Integer, primary_key=True, index=True)
    
    # Node identification
    node_name = Column(String, unique=True, index=True, nullable=False)
    node_id = Column(String, unique=True, index=True)  # Custom node ID
    cluster_name = Column(String, default="default")
    
    # Node information
    hostname = Column(String)
    ip_address = Column(String)
    region = Column(String)
    zone = Column(String)
    
    # GPU information
    gpu_count = Column(Integer, default=0)
    gpu_type = Column(String)  # e.g., "RTX 4090", "A100", "H100"
    gpu_memory_total = Column(Integer)  # Total GPU memory in MB
    gpu_memory_available = Column(Integer)  # Available GPU memory in MB
    gpu_driver_version = Column(String)
    gpu_cuda_version = Column(String)
    
    # System resources
    cpu_cores = Column(Integer)
    cpu_cores_available = Column(Integer)
    memory_total = Column(Integer)  # Total RAM in MB
    memory_available = Column(Integer)  # Available RAM in MB
    storage_total = Column(Integer)  # Total storage in GB
    storage_available = Column(Integer)  # Available storage in GB
    
    # Node status
    status = Column(String, default="pending")  # pending, active, inactive, error, maintenance
    health_status = Column(String, default="unknown")  # healthy, unhealthy, unknown
    last_heartbeat = Column(DateTime(timezone=True))
    
    # Worker configuration
    max_concurrent_jobs = Column(Integer, default=1)
    current_jobs = Column(Integer, default=0)
    auto_register = Column(Boolean, default=True)
    
    # Pricing and billing
    price_per_gpu_hour = Column(Float, default=0.0)
    price_per_cpu_hour = Column(Float, default=0.0)
    price_per_memory_gb_hour = Column(Float, default=0.0)
    
    # Kubernetes information
    k8s_node_name = Column(String)
    k8s_cluster = Column(String)
    k8s_namespace = Column(String, default="default")
    k8s_labels = Column(JSON)  # Node labels
    k8s_taints = Column(JSON)  # Node taints
    
    # Network and connectivity
    api_endpoint = Column(String)  # Worker API endpoint
    ssh_endpoint = Column(String)  # SSH endpoint for debugging
    vnc_endpoint = Column(String)  # VNC endpoint for GUI access
    
    # Metadata
    node_metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    registered_at = Column(DateTime(timezone=True))
    last_seen = Column(DateTime(timezone=True))
    
    # Relationships
    gpu_instances = relationship("GPUInstance", back_populates="node")
    jobs = relationship("GPUJob", back_populates="assigned_node")


class GPUInstance(Base):
    __tablename__ = "gpu_instances"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("gpu_nodes.id"), nullable=False)
    
    # GPU identification
    gpu_index = Column(Integer, nullable=False)  # GPU index on the node
    gpu_uuid = Column(String, unique=True, index=True)
    gpu_name = Column(String)
    
    # GPU specifications
    gpu_type = Column(String)
    gpu_memory = Column(Integer)  # GPU memory in MB
    compute_capability = Column(String)  # e.g., "8.9"
    
    # Status
    status = Column(String, default="available")  # available, busy, error, maintenance
    current_job_id = Column(Integer, ForeignKey("gpu_jobs.id"))
    utilization = Column(Float, default=0.0)  # Current GPU utilization
    temperature = Column(Float)  # GPU temperature
    power_usage = Column(Float)  # Power usage in watts
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_heartbeat = Column(DateTime(timezone=True))
    
    # Relationships
    node = relationship("GPUNode", back_populates="gpu_instances")
    current_job = relationship("GPUJob", foreign_keys=[current_job_id])


class GPUJob(Base):
    __tablename__ = "gpu_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"))
    
    # Job identification
    job_name = Column(String)
    job_type = Column(String, default="gpu_inference")  # gpu_inference, gpu_training, etc.
    
    # Docker configuration
    docker_image = Column(String, nullable=False)
    docker_tag = Column(String, default="latest")
    docker_registry = Column(String)
    docker_username = Column(String)
    docker_password = Column(String)  # Encrypted
    
    # Job configuration
    job_config = Column(JSON)  # Job-specific configuration
    input_data = Column(JSON)
    output_data = Column(JSON)
    error_message = Column(Text)
    
    # Resource requirements
    gpu_memory_required = Column(Integer)  # Required GPU memory in MB
    cpu_cores_required = Column(Integer)
    memory_required = Column(Integer)  # Required RAM in MB
    storage_required = Column(Integer)  # Required storage in GB
    
    # Job status
    status = Column(String, default="pending")  # pending, scheduled, running, completed, failed, cancelled
    
    # Assignment
    assigned_node_id = Column(Integer, ForeignKey("gpu_nodes.id"))
    assigned_gpu_id = Column(Integer, ForeignKey("gpu_instances.id"))
    
    # Kubernetes deployment
    k8s_namespace = Column(String, default="default")
    k8s_pod_name = Column(String)
    k8s_deployment_name = Column(String)
    k8s_job_name = Column(String)
    
    # Resource usage
    gpu_memory_used = Column(Integer)
    cpu_cores_used = Column(Integer)
    memory_used = Column(Integer)
    storage_used = Column(Integer)
    
    # Timing
    scheduled_at = Column(DateTime(timezone=True))
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
    user = relationship("User")
    endpoint = relationship("Endpoint")
    assigned_node = relationship("GPUNode", back_populates="jobs")
    assigned_gpu = relationship("GPUInstance", foreign_keys=[assigned_gpu_id])
    billing_account = relationship("BillingAccount")


class WorkerAgent(Base):
    __tablename__ = "worker_agents"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("gpu_nodes.id"), nullable=False)
    
    # Agent identification
    agent_id = Column(String, unique=True, index=True)
    agent_version = Column(String)
    
    # Agent status
    status = Column(String, default="pending")  # pending, active, inactive, error
    health_status = Column(String, default="unknown")
    last_heartbeat = Column(DateTime(timezone=True))
    
    # Agent configuration
    config = Column(JSON)
    capabilities = Column(JSON)  # What the agent can do
    
    # Network information
    api_endpoint = Column(String)
    websocket_endpoint = Column(String)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    
    # Relationships
    node = relationship("GPUNode")
