from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    
    # API Keys
    api_key = Column(String, unique=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Profile
    avatar_url = Column(String)
    bio = Column(Text)
    
    # Settings
    notification_preferences = Column(Text)  # JSON string
    default_worker_config = Column(Text)  # JSON string
    
    # Relationships
    jobs = relationship("Job", back_populates="user")
    created_templates = relationship("JobTemplate", back_populates="creator")
    endpoints = relationship("Endpoint", back_populates="user")
