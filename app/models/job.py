from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    delay_time = Column(Integer, default=0)  # milliseconds
    execution_time = Column(Integer, default=0)  # milliseconds
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON)
    status = Column(String, default="IN_QUEUE")  # IN_QUEUE | RUNNING | COMPLETED | FAILED | CANCELLED | TIMED_OUT
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
    executor_id = Column(Integer, ForeignKey("executors.id"), nullable=False)

    endpoint = relationship("Endpoint", back_populates="jobs")
