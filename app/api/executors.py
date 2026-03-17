from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.helpers import get_current_active_user
from app.models.user import User
from app.schemas.executor import (
    ExecutorAddRequest,
    ExecutorAddResponse,
    ExecutorShareRequest,
    ExecutorShareResponse,
    ExecutorSummary,
)
from app.services.executor_service import (
    create_executor_with_key,
    delete_executor,
    get_executors_for_user,
    share_executor,
    unshare_executor,
    list_executor_shares,
)

router = APIRouter(prefix="/executors", tags=["executors"])


@router.post("/add", response_model=ExecutorAddResponse)
def add_executor(
    body: ExecutorAddRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add an executor to the database. Returns API key and executor_id."""
    result = create_executor_with_key(db, current_user.id, body.name)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create executor")
    executor, raw_key = result
    return ExecutorAddResponse(api_key=raw_key, executor_id=executor.id)


@router.get("/", response_model=List[ExecutorSummary])
def list_user_executors(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all executors owned by or shared with the current user."""
    rows = get_executors_for_user(db, current_user.id)
    results = []
    for row in rows:
        e = row["executor"]
        summary = ExecutorSummary.model_validate(e)
        summary.is_shared = row["is_shared"]
        summary.owner = row["owner"]
        results.append(summary)
    return results


@router.post("/{executor_id}/share", response_model=ExecutorShareResponse)
def share_executor_route(
    executor_id: int,
    body: ExecutorShareRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Share an executor with another user by username. Only the owner can share."""
    try:
        share_executor(db, executor_id, current_user.id, body.username)
        return ExecutorShareResponse(executor_id=executor_id, username=body.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{executor_id}/share/{username}")
def unshare_executor_route(
    executor_id: int,
    username: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke executor sharing for a user. Only the owner can revoke."""
    try:
        if not unshare_executor(db, executor_id, current_user.id, username):
            raise HTTPException(status_code=404, detail="Share not found")
        return {"detail": "share revoked"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{executor_id}/shares", response_model=List[ExecutorShareResponse])
def list_executor_shares_route(
    executor_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List users an executor is shared with. Only the owner can view."""
    try:
        usernames = list_executor_shares(db, executor_id, current_user.id)
        return [ExecutorShareResponse(executor_id=executor_id, username=u) for u in usernames]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{executor_id}", status_code=204)
def delete_executor_route(
    executor_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete an executor and all associated resources. Only the owner can delete."""
    try:
        if not delete_executor(db, executor_id, current_user.id):
            raise HTTPException(status_code=404, detail="Executor not found")
        return None  # 204 No Content
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
