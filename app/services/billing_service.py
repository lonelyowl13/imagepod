from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.billing import BillingAccount, Transaction, Usage
from app.models.user import User
from app.schemas.billing import BillingAccountCreate, TransactionCreate, PaymentIntentCreate
import stripe
from app.config import settings
from datetime import datetime, timedelta
import json


class BillingService:
    def __init__(self, db: Session):
        self.db = db
        if settings.stripe_secret_key:
            stripe.api_key = settings.stripe_secret_key

    def create_billing_account(self, user_id: int, account_data: BillingAccountCreate) -> BillingAccount:
        # Check if user already has a primary account
        existing_primary = self.get_primary_billing_account(user_id)
        is_primary = not existing_primary

        # Create Stripe customer if not exists
        user = self.db.query(User).filter(User.id == user_id).first()
        stripe_customer_id = user.stripe_customer_id if user else None

        if not stripe_customer_id and settings.stripe_secret_key:
            try:
                stripe_customer = stripe.Customer.create(
                    email=account_data.billing_email or user.email,
                    name=account_data.name
                )
                stripe_customer_id = stripe_customer.id
                
                if user:
                    user.stripe_customer_id = stripe_customer_id
                    self.db.commit()
            except Exception as e:
                print(f"Warning: Failed to create Stripe customer: {e}")
                stripe_customer_id = None

        db_account = BillingAccount(
            user_id=user_id,
            name=account_data.name,
            billing_email=account_data.billing_email,
            auto_recharge=account_data.auto_recharge,
            auto_recharge_threshold=account_data.auto_recharge_threshold,
            auto_recharge_amount=account_data.auto_recharge_amount,
            credit_limit=account_data.credit_limit,
            spending_limit=account_data.spending_limit,
            is_primary=is_primary
        )

        self.db.add(db_account)
        self.db.commit()
        self.db.refresh(db_account)
        return db_account

    def get_billing_account(self, account_id: int, user_id: Optional[int] = None) -> Optional[BillingAccount]:
        query = self.db.query(BillingAccount).filter(BillingAccount.id == account_id)
        if user_id:
            query = query.filter(BillingAccount.user_id == user_id)
        return query.first()

    def get_primary_billing_account(self, user_id: int) -> Optional[BillingAccount]:
        return (
            self.db.query(BillingAccount)
            .filter(BillingAccount.user_id == user_id, BillingAccount.is_primary == True)
            .first()
        )

    def get_user_billing_accounts(self, user_id: int) -> List[BillingAccount]:
        return (
            self.db.query(BillingAccount)
            .filter(BillingAccount.user_id == user_id, BillingAccount.is_active == True)
            .all()
        )

    def update_billing_account(self, account_id: int, user_id: int, update_data: Dict[str, Any]) -> Optional[BillingAccount]:
        account = self.get_billing_account(account_id, user_id)
        if not account:
            return None

        for field, value in update_data.items():
            if hasattr(account, field):
                setattr(account, field, value)

        self.db.commit()
        self.db.refresh(account)
        return account

    def create_payment_intent(self, payment_data: PaymentIntentCreate) -> Dict[str, str]:
        """Create a Stripe payment intent for adding funds"""
        account = self.get_billing_account(payment_data.billing_account_id)
        if not account:
            raise ValueError("Billing account not found")

        user = self.db.query(User).filter(User.id == account.user_id).first()
        if not user or not user.stripe_customer_id:
            raise ValueError("User or Stripe customer not found")

        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(payment_data.amount * 100),  # Convert to cents
            currency=payment_data.currency,
            customer=user.stripe_customer_id,
            metadata={
                "billing_account_id": str(account.id),
                "user_id": str(user.id)
            }
        )

        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id
        }

    def process_payment_success(self, payment_intent_id: str) -> Optional[Transaction]:
        """Process successful payment and add funds to billing account"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status != "succeeded":
                return None

            billing_account_id = int(intent.metadata.get("billing_account_id"))
            amount = intent.amount / 100  # Convert from cents

            # Create transaction record
            transaction = Transaction(
                billing_account_id=billing_account_id,
                type="deposit",
                amount=amount,
                currency=intent.currency,
                description=f"Payment via Stripe",
                stripe_payment_intent_id=payment_intent_id,
                status="completed",
                processed_at=datetime.utcnow()
            )

            self.db.add(transaction)

            # Update billing account balance
            account = self.get_billing_account(billing_account_id)
            if account:
                account.balance += amount

            self.db.commit()
            self.db.refresh(transaction)
            return transaction

        except Exception as e:
            print(f"Error processing payment: {e}")
            return None

    def charge_job_cost(self, billing_account_id: int, job_id: int, amount: float, description: str = None) -> Optional[Transaction]:
        """Charge a billing account for job execution"""
        account = self.get_billing_account(billing_account_id)
        if not account:
            return None

        # Check if account has sufficient balance
        if account.balance < amount:
            # Try auto-recharge if enabled
            if account.auto_recharge and account.auto_recharge_amount > 0:
                self._trigger_auto_recharge(account)
            
            # Check again after potential recharge
            if account.balance < amount:
                return None

        # Create transaction
        transaction = Transaction(
            billing_account_id=billing_account_id,
            type="job_cost",
            amount=-amount,  # Negative for charges
            currency="USD",
            description=description or f"Job execution cost",
            job_id=job_id,
            status="completed",
            processed_at=datetime.utcnow()
        )

        self.db.add(transaction)

        # Update balance
        account.balance -= amount

        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def create_usage_record(self, billing_account_id: int, job_id: int, usage_data: Dict[str, Any]) -> Usage:
        """Create a usage record for billing"""
        usage = Usage(
            billing_account_id=billing_account_id,
            job_id=job_id,
            **usage_data
        )

        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        return usage

    def get_transactions(self, billing_account_id: int, user_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Transaction]:
        query = self.db.query(Transaction).filter(Transaction.billing_account_id == billing_account_id)
        
        if user_id:
            # Verify user owns the billing account
            account = self.get_billing_account(billing_account_id, user_id)
            if not account:
                return []

        return (
            query
            .order_by(desc(Transaction.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_usage_records(self, billing_account_id: int, user_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Usage]:
        query = self.db.query(Usage).filter(Usage.billing_account_id == billing_account_id)
        
        if user_id:
            # Verify user owns the billing account
            account = self.get_billing_account(billing_account_id, user_id)
            if not account:
                return []

        return (
            query
            .order_by(desc(Usage.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_billing_summary(self, billing_account_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get billing summary for an account"""
        account = self.get_billing_account(billing_account_id, user_id)
        if not account:
            return {}

        # Get recent transactions
        recent_transactions = self.get_transactions(billing_account_id, user_id, limit=10)
        
        # Get usage for current month
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_usage = (
            self.db.query(Usage)
            .filter(
                Usage.billing_account_id == billing_account_id,
                Usage.created_at >= current_month_start
            )
            .all()
        )

        total_monthly_cost = sum(usage.total_cost for usage in monthly_usage)

        return {
            "account": account,
            "balance": account.balance,
            "credit_limit": account.credit_limit,
            "monthly_usage": total_monthly_cost,
            "recent_transactions": recent_transactions,
            "auto_recharge": {
                "enabled": account.auto_recharge,
                "threshold": account.auto_recharge_threshold,
                "amount": account.auto_recharge_amount
            }
        }

    def _trigger_auto_recharge(self, account: BillingAccount):
        """Trigger auto-recharge for a billing account"""
        if not account.auto_recharge or account.auto_recharge_amount <= 0:
            return

        # Create payment intent for auto-recharge
        try:
            payment_data = PaymentIntentCreate(
                amount=account.auto_recharge_amount,
                billing_account_id=account.id
            )
            
            payment_intent = self.create_payment_intent(payment_data)
            
            # In a real implementation, you would handle the payment flow
            # For now, we'll just log it
            print(f"Auto-recharge triggered for account {account.id}: ${account.auto_recharge_amount}")
            
        except Exception as e:
            print(f"Auto-recharge failed for account {account.id}: {e}")
