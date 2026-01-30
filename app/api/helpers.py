from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import verify_token, get_user_by_username
from app.services.api_key_service import get_user_by_api_key

security = HTTPBearer()


def get_user_by_credentials(db: Session, credentials: str) -> Optional[User]:
    """
    Resolve a user from either an access token (JWT) or an API key.
    Tries JWT first, then API key. Returns None if neither is valid.
    """
    # Try access token (JWT) first
    username = verify_token(credentials)
    if username is not None:
        user = get_user_by_username(db, username)
        if user is not None:
            return user
    # Fall back to API key
    return get_user_by_api_key(db, credentials)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = get_user_by_credentials(db, credentials.credentials)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
