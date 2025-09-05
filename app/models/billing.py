from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class BillingAccount(Base):
    __tablename__ = "billing_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Account info
    name = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Billing settings
    billing_email = Column(String)
    payment_method_id = Column(String)  # Stripe payment method ID
    auto_recharge = Column(Boolean, default=False)
    auto_recharge_threshold = Column(Float, default=10.0)
    auto_recharge_amount = Column(Float, default=50.0)
    
    # Balance and limits
    balance = Column(Float, default=0.0)
    credit_limit = Column(Float, default=0.0)
    spending_limit = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="billing_accounts")
    transactions = relationship("Transaction", back_populates="billing_account")
    usage_records = relationship("Usage", back_populates="billing_account")
    jobs = relationship("Job", back_populates="billing_account")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    billing_account_id = Column(Integer, ForeignKey("billing_accounts.id"), nullable=False)
    
    # Transaction details
    type = Column(String, nullable=False)  # deposit, withdrawal, job_cost, refund
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    description = Column(Text)
    
    # External references
    stripe_payment_intent_id = Column(String)
    stripe_charge_id = Column(String)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    
    # Status
    status = Column(String, default="pending")  # pending, completed, failed, refunded
    
    # Metadata
    transaction_metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # Relationships
    billing_account = relationship("BillingAccount", back_populates="transactions")
    job = relationship("Job")


class Usage(Base):
    __tablename__ = "usage"

    id = Column(Integer, primary_key=True, index=True)
    billing_account_id = Column(Integer, ForeignKey("billing_accounts.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    
    # Usage metrics
    gpu_seconds = Column(Float, default=0.0)
    cpu_seconds = Column(Float, default=0.0)
    memory_seconds = Column(Float, default=0.0)  # MB-seconds
    storage_seconds = Column(Float, default=0.0)  # GB-seconds
    
    # Cost breakdown
    gpu_cost = Column(Float, default=0.0)
    cpu_cost = Column(Float, default=0.0)
    memory_cost = Column(Float, default=0.0)
    storage_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Time period
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    billing_account = relationship("BillingAccount", back_populates="usage_records")
    job = relationship("Job")
