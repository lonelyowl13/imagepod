from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Endpoint(Base):
    """Endpoint entity per endpoints.txt: template + executor + config"""
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint_id = Column(String, unique=True, index=True)  # API "id" (e.g. "jpnw0v75y3qoql")
    name = Column(String, nullable=False)
    template_id = Column(String, ForeignKey("templates.template_id"), nullable=False)
    executor_id = Column(Integer, ForeignKey("executors.id"), nullable=False)

    compute_type = Column(String, default="GPU")
    execution_timeout_ms = Column(Integer, default=600000)
    idle_timeout = Column(Integer, default=5)
    vcpu_count = Column(Integer, default=2)
    env = Column(JSON)  # env vars (can override template)
    version = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="endpoints")
    template = relationship(
        "Template",
        foreign_keys=[template_id],
        primaryjoin="Endpoint.template_id == Template.template_id",
    )
    executor = relationship("Executor", back_populates="endpoints")
    jobs = relationship("Job", back_populates="endpoint")
