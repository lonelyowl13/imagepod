from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Executor(Base):
    __tablename__ = "executors"

    id = Column(Integer, primary_key=True, index=True)
    
    # Executor identification
    executor_id = Column(String, unique=True, index=True)  # Custom executor ID
    name = Column(String)
    
    # Machine information (to be expanded later)
    gpu_type = Column(String)  # e.g., "NVIDIA GeForce RTX 4090"
    gpu_count = Column(Integer, default=1)
    cuda_version = Column(String)  # e.g., "12.9"
    compute_type = Column(String, default="GPU")  # GPU, CPU, etc.
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    metadata = Column(JSON)  # Additional machine info
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_heartbeat = Column(DateTime(timezone=True))
    
    # Relationships
    endpoints = relationship("Endpoint", back_populates="executor")
