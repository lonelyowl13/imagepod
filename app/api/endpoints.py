from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.api.helpers import get_current_active_user
from app.models.user import User
from app.schemas.endpoint import (
    EndpointCreate, EndpointUpdate, EndpointResponse, ExecutorResponse
)
from app.schemas.template import TemplateResponse
from app.rabbitmq import publish_job_notification

router = APIRouter(prefix="/endpoints", tags=["endpoints"])


def _format_template_response(template) -> TemplateResponse:
    """Format template for endpoint response"""
    return TemplateResponse(
        id=template.id,
        name=template.name,
        image_name=template.image_name,
        docker_entrypoint=template.docker_entrypoint or [],
        docker_start_cmd=template.docker_start_cmd or [],
        env=template.env or {},
    )


def _format_executor_response(executor) -> ExecutorResponse:
    """Format executor for endpoint response"""
    return ExecutorResponse(
        id=executor.id,
        name=executor.name,
        gpu_type=getattr(executor, "gpu", None) or getattr(executor, "gpu_type", None),
        gpu_count=getattr(executor, "gpu_count", 1),
        cuda_version=executor.cuda_version,
        compute_type=executor.compute_type or "GPU",
        is_active=executor.is_active,
    )


def _format_endpoint_response(endpoint) -> EndpointResponse:
    """Format endpoint for response"""
    return EndpointResponse(
        id=endpoint.id,
        name=endpoint.name,
        compute_type=endpoint.compute_type,
        executor_id=endpoint.executor.id,
        execution_timeout_ms=endpoint.execution_timeout_ms,
        idle_timeout=endpoint.idle_timeout,
        template_id=endpoint.template_id,
        vcpu_count=endpoint.vcpu_count,
        env=endpoint.env or {},
        version=endpoint.version,
        status=getattr(endpoint, "status", "Deploying"),
        created_at=endpoint.created_at,
        template=_format_template_response(endpoint.template),
        executor=_format_executor_response(endpoint.executor),
        user_id=endpoint.user_id,
    )


@router.post("/", response_model=EndpointResponse, status_code=status.HTTP_200_OK)
async def create_endpoint(
    request: Request,
    endpoint_data: EndpointCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create an endpoint from template"""
    from app.services.endpoint_service import create_endpoint as svc_create, get_endpoint
    try:
        endpoint = svc_create(db, current_user.id, endpoint_data)
        endpoint = get_endpoint(db, endpoint.id, current_user.id)
        conn = getattr(request.app.state, "rabbitmq", None)
        if conn:
            await publish_job_notification(conn, endpoint.executor_id)
        return _format_endpoint_response(endpoint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[EndpointResponse])
async def list_endpoints(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List user endpoints"""
    from app.services.endpoint_service import get_user_endpoints
    endpoints = get_user_endpoints(db, current_user.id)
    return [_format_endpoint_response(e) for e in endpoints]


@router.get("/{id}", response_model=EndpointResponse)
async def get_endpoint_route(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific endpoint"""
    from app.services.endpoint_service import get_endpoint
    endpoint = get_endpoint(db, id, current_user.id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return _format_endpoint_response(endpoint)


@router.patch("/{id}", response_model=EndpointResponse)
async def update_endpoint_route(
    request: Request,
    id: int,
    endpoint_update: EndpointUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an endpoint"""
    from app.services.endpoint_service import update_endpoint, get_endpoint
    try:
        updated = update_endpoint(db, id, endpoint_update, current_user.id)
        if not updated:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        updated = get_endpoint(db, id, current_user.id)
        conn = getattr(request.app.state, "rabbitmq", None)
        if conn:
            await publish_job_notification(conn, updated.executor_id)
        return _format_endpoint_response(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_endpoint_route(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete an endpoint"""
    from app.services.endpoint_service import delete_endpoint
    if not delete_endpoint(db, id, current_user.id):
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return {"message": "Endpoint deleted successfully"}

