from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth import get_current_active_user
from app.models.user import User
from app.schemas.endpoint import (
    EndpointCreate, EndpointUpdate, EndpointResponse, ExecutorResponse
)
from app.schemas.template import TemplateResponse
from app.services.endpoint_service import EndpointService

router = APIRouter(prefix="/endpoints", tags=["endpoints"])


def _format_template_response(template) -> TemplateResponse:
    """Format template for endpoint response"""
    from app.schemas.template import TemplateResponse
    return TemplateResponse(
        id=template.template_id,
        name=template.name,
        image_name=template.image_name,
        category=template.category,
        container_disk_in_gb=template.container_disk_in_gb,
        container_registry_auth_id=template.container_registry_auth_id,
        docker_entrypoint=template.docker_entrypoint or [],
        docker_start_cmd=template.docker_start_cmd or [],
        env=template.env or {},
        ports=template.ports or [],
        readme=template.readme or "",
        volume_in_gb=template.volume_in_gb,
        volume_mount_path=template.volume_mount_path,
        is_public=template.is_public,
        is_serverless=template.is_serverless,
        earned=template.earned,
        runtime_in_min=template.runtime_in_min,
        is_runpod=template.is_runpod
    )


def _format_executor_response(executor) -> ExecutorResponse:
    """Format executor for endpoint response"""
    return ExecutorResponse(
        id=str(executor.id),  # Convert to string as per spec
        name=executor.name,
        gpu_type=executor.gpu_type,
        gpu_count=executor.gpu_count,
        cuda_version=executor.cuda_version,
        compute_type=executor.compute_type,
        is_active=executor.is_active,
        is_online=executor.is_online
    )


def _format_endpoint_response(endpoint) -> EndpointResponse:
    """Format endpoint for response matching RunPod API format"""
    return EndpointResponse(
        id=endpoint.endpoint_id,
        name=endpoint.name,
        allowed_cuda_versions=endpoint.allowed_cuda_versions or [],
        compute_type=endpoint.compute_type,
        executor_id=str(endpoint.executor.id),  # String representation
        execution_timeout_ms=endpoint.execution_timeout_ms,
        idle_timeout=endpoint.idle_timeout,
        template_id=endpoint.template_id,
        vcpu_count=endpoint.vcpu_count,
        env=endpoint.env or {},
        version=endpoint.version,
        created_at=endpoint.created_at,
        template=_format_template_response(endpoint.template),
        executor=_format_executor_response(endpoint.executor),
        user_id=str(endpoint.user_id)  # String representation
    )


@router.post("/", response_model=EndpointResponse, status_code=status.HTTP_200_OK)
async def create_endpoint(
    endpoint_data: EndpointCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create an endpoint from template"""
    endpoint_service = EndpointService(db)
    
    try:
        endpoint = endpoint_service.create_endpoint(current_user.id, endpoint_data)
        # Reload with relationships
        endpoint = endpoint_service.get_endpoint(endpoint.endpoint_id, current_user.id)
        return _format_endpoint_response(endpoint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")


@router.get("/", response_model=List[EndpointResponse])
async def get_endpoints(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user endpoints"""
    endpoint_service = EndpointService(db)
    endpoints = endpoint_service.get_user_endpoints(current_user.id)
    return [_format_endpoint_response(e) for e in endpoints]


@router.get("/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint(
    endpoint_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific endpoint"""
    endpoint_service = EndpointService(db)
    endpoint = endpoint_service.get_endpoint(endpoint_id, current_user.id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return _format_endpoint_response(endpoint)


@router.patch("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: str,
    endpoint_update: EndpointUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an endpoint"""
    endpoint_service = EndpointService(db)
    
    # Validate endpoint ID format
    if not endpoint_id or len(endpoint_id) < 1:
        raise HTTPException(status_code=400, detail="Invalid endpoint id supplied")
    
    try:
        updated_endpoint = endpoint_service.update_endpoint(endpoint_id, endpoint_update, current_user.id)
        if not updated_endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        # Reload with relationships
        updated_endpoint = endpoint_service.get_endpoint(endpoint_id, current_user.id)
        return _format_endpoint_response(updated_endpoint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{endpoint_id}", status_code=status.HTTP_200_OK)
async def delete_endpoint(
    endpoint_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an endpoint"""
    endpoint_service = EndpointService(db)
    
    # Validate endpoint ID format
    if not endpoint_id or len(endpoint_id) < 1:
        raise HTTPException(status_code=400, detail="Invalid endpoint id supplied")
    
    success = endpoint_service.delete_endpoint(endpoint_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return {"message": "Endpoint deleted successfully"}


@router.post("/{endpoint_id}/update", response_model=EndpointResponse)
async def update_endpoint_synonym(
    endpoint_id: str,
    endpoint_update: EndpointUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an endpoint (synonym for PATCH /endpoints/{endpoint_id})"""
    # Reuse the same logic as PATCH
    return await update_endpoint(endpoint_id, endpoint_update, current_user, db)
