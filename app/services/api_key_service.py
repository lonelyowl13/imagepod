import hashlib
import secrets
import string
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from app.models.user import User
from app.models.api_key import ApiKey


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_api_key() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def create_api_key(db: Session, user_id: int) -> Optional[Tuple[int, str]]:
    """Create a new API key for the user. Returns (key_id, raw_key). Raw key is shown once."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    raw_key = _generate_api_key()
    key_hash = _hash_key(raw_key)
    row = ApiKey(user_id=user_id, key_hash=key_hash)
    db.add(row)
    db.commit()
    db.refresh(row)
    return (row.id, raw_key)


def delete_api_key(db: Session, user_id: int, key_id: int) -> bool:
    """Delete an API key if it belongs to the user."""
    row = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def get_user_by_api_key(db: Session, api_key: str) -> Optional[User]:
    """Resolve user from API key (lookup by hash)."""
    key_hash = _hash_key(api_key)
    row = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
    if not row:
        return None
    return db.query(User).filter(User.id == row.user_id).first()


def list_keys(db: Session, user_id: int) -> List[dict]:
    """List API key metadata for the user (id, created_at). Does not return the key value."""
    rows = db.query(ApiKey).filter(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc()).all()
    return [{"id": r.id, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]
