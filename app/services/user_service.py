from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.auth_service import get_password_hash, verify_password


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


def change_password(db: Session, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.hashed_password):
        raise ValueError("Incorrect password")
    user.hashed_password = get_password_hash(new_password)
    db.commit()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()
