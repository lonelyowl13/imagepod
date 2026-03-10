from sqlalchemy import BigInteger, Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Executor(Base):
    __tablename__ = "executors"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(64), unique=True, index=True)  # SHA-256 of API key; set when executor is added
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

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
    endpoints = relationship("Endpoint", back_populates="executor", cascade="all, delete-orphan")
    volumes = relationship("Volume", back_populates="executor", cascade="all, delete-orphan")
    user = relationship("User", back_populates="executors")
    shares = relationship("ExecutorShare", back_populates="executor", cascade="all, delete-orphan")
    pods = relationship("Pod", back_populates="executor")


class ExecutorShare(Base):
    __tablename__ = "executor_shares"

    id = Column(Integer, primary_key=True, index=True)
    executor_id = Column(Integer, ForeignKey("executors.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    executor = relationship("Executor", back_populates="shares")
    user = relationship("User")

    __table_args__ = (UniqueConstraint("executor_id", "user_id", name="uq_executor_share"),)