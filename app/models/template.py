from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Template identification
    template_id = Column(String, unique=True, index=True)  # Custom template ID (e.g., "30zmvf89kd")
    name = Column(String, nullable=False)
    
    # Docker configuration
    image_name = Column(String, nullable=False)
    docker_entrypoint = Column(JSON)  # Array of strings
    docker_start_cmd = Column(JSON)  # Array of strings
    
    # Container configuration
    category = Column(String)  # e.g., "NVIDIA"
    container_disk_in_gb = Column(Integer, default=50)
    container_registry_auth_id = Column(String)  # Registry authentication ID
    
    # Environment variables
    env = Column(JSON)  # Dictionary of env vars
    
    # Ports (for compatibility, unused)
    ports = Column(JSON)  # Array of strings like ["8888/http", "22/tcp"]
    
    # Volume configuration (unused, for compatibility)
    volume_in_gb = Column(Integer, default=20)
    volume_mount_path = Column(String, default="/workspace")
    
    # Metadata
    readme = Column(Text, default="")
    is_public = Column(Boolean, default=False)  # Unused but kept for compatibility
    is_serverless = Column(Boolean, default=True)  # Always True for now
    
    # Statistics (response fields)
    earned = Column(Integer, default=0)  # Earnings/credits
    runtime_in_min = Column(Integer, default=0)  # Total runtime in minutes
    is_runpod = Column(Boolean, default=False)  # Whether it's a RunPod template
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="templates")

