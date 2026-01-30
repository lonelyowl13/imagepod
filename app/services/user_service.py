from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.auth_service import get_password_hash


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, username: str, password: str) -> User:
        if self.get_user_by_username(username):
            raise ValueError("Username already taken")
        hashed_password = get_password_hash(password)
        db_user = User(
            username=username,
            hashed_password=hashed_password,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()
