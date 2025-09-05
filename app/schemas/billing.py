from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class BillingAccountBase(BaseModel):
    name: str
    billing_email: Optional[str] = None
    auto_recharge: bool = False
    auto_recharge_threshold: float = 10.0
    auto_recharge_amount: float = 50.0
    credit_limit: float = 0.0
    spending_limit: Optional[float] = None


class BillingAccountCreate(BillingAccountBase):
    pass


class BillingAccountResponse(BillingAccountBase):
    id: int
    user_id: int
    is_primary: bool
    is_active: bool
    balance: float
    payment_method_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    type: str
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    transaction_metadata: Optional[Dict[str, Any]] = None


class TransactionCreate(TransactionBase):
    billing_account_id: int


class TransactionResponse(TransactionBase):
    id: int
    billing_account_id: int
    stripe_payment_intent_id: Optional[str] = None
    stripe_charge_id: Optional[str] = None
    job_id: Optional[int] = None
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UsageResponse(BaseModel):
    id: int
    billing_account_id: int
    job_id: int
    gpu_seconds: float
    cpu_seconds: float
    memory_seconds: float
    storage_seconds: float
    gpu_cost: float
    cpu_cost: float
    memory_cost: float
    storage_cost: float
    total_cost: float
    start_time: datetime
    end_time: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentIntentCreate(BaseModel):
    amount: float
    currency: str = "USD"
    billing_account_id: int


class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str
