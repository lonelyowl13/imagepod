from sqlalchemy import BigInteger, Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Executor(Base):
    __tablename__ = "executors"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(64), unique=True, index=True)  # SHA-256 of API key; set when executor is added

    name = Column(String)
    
    gpu = Column(String)  # e.g., "NVIDIA GeForce RTX 4090"
    cpu = Column(String)
    ram = Column(BigInteger) # total ram in bytes
    vram = Column(BigInteger) # total vram in bytes 
    
    cuda_version = Column(String)  # e.g., "12.9"
    compute_type = Column(String)  # GPU, CPU, etc.
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    metadata_ = Column("metadata", JSON)  # Additional machine info
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_heartbeat = Column(DateTime(timezone=True))
    
    # Relationships
    endpoints = relationship("Endpoint", back_populates="executor")
