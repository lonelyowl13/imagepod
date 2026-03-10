from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import EntityKind, NotificationType
from app.api.helpers import format_template_response, get_current_active_user
from app.models.user import User
from app.services.notification_service import create_notification
from app.schemas.pod import PodCreate, PodUpdate, PodResponse
from app.schemas.endpoint import ExecutorResponse
from app.services.pod_service import (
    create_pod as svc_create,
    get_pod,
    get_user_pods,
    update_pod,
    delete_pod,
    start_pod,
    stop_pod,
)


router = APIRouter(prefix="/pods", tags=["pods"])


def _format_executor_response(executor) -> ExecutorResponse:
    return ExecutorResponse(
        id=executor.id,
        name=executor.name,
        gpu_type=getattr(executor, "gpu", None) or getattr(executor, "gpu_type", None),
        gpu_count=getattr(executor, "gpu_count", 1),
        cuda_version=executor.cuda_version,
        compute_type=executor.compute_type or "GPU",
        is_active=executor.is_active,
    )


def _format_pod_response(pod) -> PodResponse:
    return PodResponse(
        id=pod.id,
        name=pod.name,
        compute_type=pod.compute_type,
        executor_id=pod.executor.id,
        template_id=pod.template_id,
        vcpu_count=pod.vcpu_count,
        env=pod.env or {},
        ports=pod.ports or [],
        status=pod.status,
        created_at=pod.created_at,
        last_started_at=pod.last_started_at,
        last_stopped_at=pod.last_stopped_at,
        template=format_template_response(pod.template),
        executor=_format_executor_response(pod.executor),
        user_id=pod.user_id,
    )


@router.post("/", response_model=PodResponse, status_code=status.HTTP_200_OK)
async def create_pod_route(
    body: PodCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new pod from template."""
    try:
        pod = svc_create(db, current_user.id, body)
        pod = get_pod(db, pod.id, current_user.id)
        payload = _format_pod_response(pod).model_dump(mode="json")
        create_notification(db, pod.executor_id, NotificationType.POD_STATUS_CHANGED, EntityKind.POD, pod.id, payload)
        return _format_pod_response(pod)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[PodResponse])
async def list_pods(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List current user's pods."""
    pods = get_user_pods(db, current_user.id)
    return [_format_pod_response(p) for p in pods]


@router.get("/{id}", response_model=PodResponse)
async def get_pod_route(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a pod by id."""
    pod = get_pod(db, id, current_user.id)
    if not pod:
        raise HTTPException(status_code=404, detail="Pod not found")
    return _format_pod_response(pod)


@router.patch("/{id}", response_model=PodResponse)
async def update_pod_route(
    id: int,
    body: PodUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a pod."""
    try:
        pod = update_pod(db, id, body, current_user.id)
        if not pod:
            raise HTTPException(status_code=404, detail="Pod not found")
        pod = get_pod(db, id, current_user.id)
        payload = _format_pod_response(pod).model_dump(mode="json")
        create_notification(db, pod.executor_id, NotificationType.POD_STATUS_CHANGED, EntityKind.POD, pod.id, payload)
        return _format_pod_response(pod)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_pod_route(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a pod."""
    pod = get_pod(db, id, current_user.id)
    if not pod:
        raise HTTPException(status_code=404, detail="Pod not found")
    payload = _format_pod_response(pod).model_dump(mode="json")
    executor_id = pod.executor_id
    entity_id = pod.id
    delete_pod(db, id, current_user.id)
    create_notification(db, executor_id, NotificationType.POD_STATUS_CHANGED, EntityKind.POD, entity_id, payload)
    return {"message": "Pod deleted successfully"}


@router.post("/{id}/start", response_model=PodResponse)
async def start_pod_route(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Start a stopped pod."""
    try:
        pod = start_pod(db, id, current_user.id)
        if not pod:
            raise HTTPException(status_code=404, detail="Pod not found")
        pod = get_pod(db, id, current_user.id)
        payload = _format_pod_response(pod).model_dump(mode="json")
        create_notification(db, pod.executor_id, NotificationType.POD_STATUS_CHANGED, EntityKind.POD, pod.id, payload)
        return _format_pod_response(pod)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id}/stop", response_model=PodResponse)
async def stop_pod_route(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Stop a running pod."""
    pod = stop_pod(db, id, current_user.id)
    if not pod:
        raise HTTPException(status_code=404, detail="Pod not found")
    pod = get_pod(db, id, current_user.id)
    payload = _format_pod_response(pod).model_dump(mode="json")
    create_notification(db, pod.executor_id, NotificationType.POD_STATUS_CHANGED, EntityKind.POD, pod.id, payload)
    return _format_pod_response(pod)

