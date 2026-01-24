from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth import get_current_active_user
from app.models.user import User
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse
from app.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"])


def _format_template_response(template) -> TemplateResponse:
    """Format template for response matching RunPod API format"""
    return TemplateResponse(
        id=template.template_id,
        name=template.name,
        image_name=template.image_name,  # Will be serialized as imageName
        category=template.category,
        container_disk_in_gb=template.container_disk_in_gb,  # Will be serialized as containerDiskInGb
        container_registry_auth_id=template.container_registry_auth_id,  # Will be serialized as containerRegistryAuthId
        docker_entrypoint=template.docker_entrypoint or [],  # Will be serialized as dockerEntrypoint
        docker_start_cmd=template.docker_start_cmd or [],  # Will be serialized as dockerStartCmd
        env=template.env or {},
        ports=template.ports or [],
        readme=template.readme or "",
        volume_in_gb=template.volume_in_gb,  # Will be serialized as volumeInGb
        volume_mount_path=template.volume_mount_path,  # Will be serialized as volumeMountPath
        is_public=template.is_public,  # Will be serialized as isPublic
        is_serverless=template.is_serverless,  # Will be serialized as isServerless
        earned=template.earned,
        runtime_in_min=template.runtime_in_min,  # Will be serialized as runtimeInMin
        is_runpod=template.is_runpod  # Will be serialized as isRunpod
    )


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_200_OK)
async def create_template(
    template_data: TemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new template"""
    template_service = TemplateService(db)
    
    try:
        template = template_service.create_template(current_user.id, template_data)
        return _format_template_response(template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")


@router.get("/", response_model=List[TemplateResponse])
async def get_templates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user templates"""
    template_service = TemplateService(db)
    templates = template_service.get_user_templates(current_user.id)
    return [_format_template_response(t) for t in templates]


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific template"""
    template_service = TemplateService(db)
    template = template_service.get_template(template_id, current_user.id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return _format_template_response(template)


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    template_update: TemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a template"""
    template_service = TemplateService(db)
    
    # Validate template ID format
    if not template_id or len(template_id) < 1:
        raise HTTPException(status_code=400, detail="Invalid template id supplied")
    
    updated_template = template_service.update_template(template_id, template_update, current_user.id)
    if not updated_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return _format_template_response(updated_template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a template"""
    template_service = TemplateService(db)
    
    # Validate template ID format
    if not template_id or len(template_id) < 1:
        raise HTTPException(status_code=400, detail="Invalid template id supplied")
    
    success = template_service.delete_template(template_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return None


@router.post("/{template_id}/update", response_model=TemplateResponse)
async def update_template_synonym(
    template_id: str,
    template_update: TemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a template (synonym for PATCH /templates/{template_id})"""
    # Reuse the same logic as PATCH
    return await update_template(template_id, template_update, current_user, db)

