from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.enums import PodStatus


class Pod(Base):
    __tablename__ = "pods"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)

    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    executor_id = Column(Integer, ForeignKey("executors.id"), nullable=False, index=True)

    compute_type = Column(String, default="GPU")
    vcpu_count = Column(Integer, default=2)
    env = Column(JSON)
    ports = Column(JSON)
    status = Column(String, default=PodStatus.STOPPED, server_default=PodStatus.STOPPED.value)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_started_at = Column(DateTime(timezone=True), nullable=True)
    last_stopped_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="pods")
    template = relationship("Template", backref="pods")
    executor = relationship("Executor", back_populates="pods")

