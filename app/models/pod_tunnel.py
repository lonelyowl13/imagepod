from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PodTunnel(Base):
    __tablename__ = "pod_tunnels"

    id = Column(Integer, primary_key=True, index=True)
    pod_id = Column(Integer, ForeignKey("pods.id", ondelete="CASCADE"), nullable=False, index=True)
    port = Column(Integer, nullable=False)
    # 8 random hex chars prepended to the subdomain to prevent enumeration
    token = Column(String(8), nullable=False)
    domain = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pod = relationship("Pod", back_populates="tunnels")
