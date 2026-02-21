from sqlalchemy import Column, DateTime, Index, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_executor_status", "executor_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    delay_time = Column(Integer, default=0)  # milliseconds
    execution_time = Column(Integer, default=0)  # milliseconds
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON)
    status = Column(String, default="IN_QUEUE", index=True)  # IN_QUEUE | RUNNING | COMPLETED | FAILED | CANCELLED | TIMED_OUT
    endpoint_id = Column(Integer, ForeignKey("endpoints.id", ondelete="CASCADE"), nullable=False)
    executor_id = Column(Integer, ForeignKey("executors.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    endpoint = relationship("Endpoint", back_populates="jobs")
