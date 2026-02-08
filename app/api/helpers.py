from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.executor import EndpointUpdateItem, ExecutorUpdatesResponse
from app.schemas.job import JobResponse
from app.schemas.template import TemplateResponse
from app.services.auth_service import verify_token, get_user_by_username
from app.services.api_key_service import get_user_by_api_key
from app.services.executor_service import get_endpoints_for_executor_by_status, get_executor_by_api_key, get_jobs_in_queue

security = HTTPBearer()

def format_template_response(template) -> TemplateResponse:
    return TemplateResponse(
        id=template.id,
        name=template.name,
        image_name=template.image_name,
        docker_entrypoint=template.docker_entrypoint or [],
        docker_start_cmd=template.docker_start_cmd or [],
        env=template.env or {},
    )


def build_updates_response(db: Session, executor_id: int) -> ExecutorUpdatesResponse:
    """Build unified updates: jobs IN_QUEUE + endpoints with status Deploying."""
    jobs = get_jobs_in_queue(db, executor_id)
    endpoints = get_endpoints_for_executor_by_status(db, executor_id, "Deploying")
    return ExecutorUpdatesResponse(
        jobs=[
            JobResponse(
                id=j.id,
                delay_time=j.delay_time,
                execution_time=j.execution_time,
                output=j.output_data,
                input=j.input_data,
                status=j.status,
                endpoint_id=j.endpoint_id,
                executor_id=j.executor_id,
            )
            for j in jobs
        ],
        endpoints=[
            EndpointUpdateItem(
                id=e.id,
                name=e.name,
                status=e.status,
                template_id=e.template_id,
                executor_id=e.executor_id,
                template=format_template_response(e.template),
                env=e.env or {},
                version=e.version,
            )
            for e in endpoints
        ],
    )
    

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


async def get_current_executor(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Resolve executor from Bearer token (executor API key). Used by executor-only routes."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid executor credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    executor = get_executor_by_api_key(db, credentials.credentials)
    if executor is None:
        raise credentials_exception
    return executor
