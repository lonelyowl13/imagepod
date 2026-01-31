from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class Job(Base):
    """Compact job entity per jobs.txt: id, delay_time, execution_time, input, output, status, endpoint_id, executor_id"""
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    delay_time = Column(Integer, default=0)  # milliseconds
    execution_time = Column(Integer, default=0)  # milliseconds
    input_data = Column(JSON, nullable=False)  # input
    output_data = Column(JSON)  # output
    status = Column(String, default="IN_QUEUE")  # IN_QUEUE | RUNNING | COMPLETED | FAILED | CANCELLED | TIMED_OUT
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
    executor_id = Column(Integer, ForeignKey("executors.id"), nullable=False)

    # Relationships
    endpoint = relationship("Endpoint", back_populates="jobs")
