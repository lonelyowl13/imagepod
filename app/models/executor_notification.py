from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ExecutorNotification(Base):
    __tablename__ = "executor_notifications"

    id = Column(Integer, primary_key=True, index=True)
    executor_id = Column(Integer, ForeignKey("executors.id"), nullable=False, index=True)

    type = Column(String, nullable=False)
    entity_kind = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)

    acknowledged = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    executor = relationship("Executor", back_populates="notifications")

