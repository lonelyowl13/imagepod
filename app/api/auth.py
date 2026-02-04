from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.api.helpers import get_current_active_user
from app.database import get_db
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.schemas.user import (
    ApiKey,
    ApiKeyMetadata,
    KeyList,
    RegisterRequest,
    UserResponse,
    LoginRequest,
    Token,
    RefreshRequest,
)
from app.services.user_service import UserService
from app.services.api_key_service import (
    create_api_key as create_api_key_record,
    delete_api_key,
    list_keys,
)
from app.config import settings
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Body: username, password, password2."""
    user_service = UserService(db)
    try:
        user = user_service.create_user(body.username, body.password)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Login with username and password. Returns access_token and refresh_token."""
    user = authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh_token in body."""
    username = verify_refresh_token(body.refresh_token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_service = UserService(db)
    user = user_service.get_user_by_username(username)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get("/keys", response_model=KeyList)
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List API key metadata (id, created_at) for the current user. Does not return key values."""

    return KeyList(keys=[ApiKeyMetadata(id=k["id"], created_at=k["created_at"]) for k in list_keys(db, current_user.id)])



@router.get("/key", response_model=ApiKey)
async def create_api_key(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new API key for the current user. Returns id and api_key (shown once)."""
    result = create_api_key_record(db, current_user.id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create API key")
    key_id, raw_key = result
    
    return ApiKey(id=key_id, api_key=raw_key)


@router.delete("/key/{key_id}")
async def delete_api_key_route(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete an API key by id. Key must belong to the current user."""
    if not delete_api_key(db, current_user.id, key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    return "API key deleted"
