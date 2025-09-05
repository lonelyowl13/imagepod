from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.auth import get_current_active_user
from app.models.user import User
from app.schemas.billing import (
    BillingAccountCreate, BillingAccountResponse, 
    TransactionResponse, UsageResponse, PaymentIntentCreate, PaymentIntentResponse
)
from app.services.billing_service import BillingService

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/accounts/", response_model=BillingAccountResponse)
async def create_billing_account(
    account_data: BillingAccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new billing account"""
    billing_service = BillingService(db)
    
    try:
        account = billing_service.create_billing_account(current_user.id, account_data)
        return account
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts/", response_model=List[BillingAccountResponse])
async def get_user_billing_accounts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's billing accounts"""
    billing_service = BillingService(db)
    accounts = billing_service.get_user_billing_accounts(current_user.id)
    return accounts


@router.get("/accounts/{account_id}", response_model=BillingAccountResponse)
async def get_billing_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific billing account"""
    billing_service = BillingService(db)
    account = billing_service.get_billing_account(account_id, current_user.id)
    
    if not account:
        raise HTTPException(status_code=404, detail="Billing account not found")
    
    return account


@router.get("/accounts/{account_id}/summary")
async def get_billing_summary(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get billing summary for an account"""
    billing_service = BillingService(db)
    summary = billing_service.get_billing_summary(account_id, current_user.id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Billing account not found")
    
    return summary


@router.post("/payment-intents/", response_model=PaymentIntentResponse)
async def create_payment_intent(
    payment_data: PaymentIntentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a payment intent for adding funds"""
    billing_service = BillingService(db)
    
    try:
        payment_intent = billing_service.create_payment_intent(payment_data)
        return payment_intent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payment-intents/{payment_intent_id}/confirm")
async def confirm_payment(
    payment_intent_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Confirm a payment intent"""
    billing_service = BillingService(db)
    transaction = billing_service.process_payment_success(payment_intent_id)
    
    if not transaction:
        raise HTTPException(status_code=400, detail="Payment confirmation failed")
    
    return {"message": "Payment confirmed successfully", "transaction": transaction}


@router.get("/accounts/{account_id}/transactions/", response_model=List[TransactionResponse])
async def get_transactions(
    account_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get transactions for a billing account"""
    billing_service = BillingService(db)
    transactions = billing_service.get_transactions(account_id, current_user.id, skip, limit)
    return transactions


@router.get("/accounts/{account_id}/usage/", response_model=List[UsageResponse])
async def get_usage_records(
    account_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get usage records for a billing account"""
    billing_service = BillingService(db)
    usage_records = billing_service.get_usage_records(account_id, current_user.id, skip, limit)
    return usage_records
