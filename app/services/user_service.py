from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.auth_service import get_password_hash


def create_user(db: Session, username: str, password: str) -> User:
    if get_user_by_username(db, username):
        raise ValueError("Username already taken")
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()
