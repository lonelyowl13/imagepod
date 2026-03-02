from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Volume(Base):
    __tablename__ = "volumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    executor_id = Column(Integer, ForeignKey("executors.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    size_gb = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="volumes")
    executor = relationship("Executor", back_populates="volumes")
    mounts = relationship("EndpointVolume", back_populates="volume", cascade="all, delete-orphan")


class EndpointVolume(Base):
    """Association between endpoints and volumes with a per-mount path."""
    __tablename__ = "endpoint_volumes"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id", ondelete="CASCADE"), nullable=False)
    volume_id = Column(Integer, ForeignKey("volumes.id", ondelete="CASCADE"), nullable=False)
    mount_path = Column(String, nullable=False, default="/runpod-volume")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("endpoint_id", "volume_id", name="uq_endpoint_volume"),
    )

    endpoint = relationship("Endpoint", back_populates="volume_mounts")
    volume = relationship("Volume", back_populates="mounts")
