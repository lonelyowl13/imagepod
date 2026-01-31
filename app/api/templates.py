from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.helpers import get_current_active_user
from app.models.user import User
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse
from app.services.template_service import (
    create_template,
    get_template,
    get_user_templates,
    update_template,
    delete_template,
)

router = APIRouter(prefix="/templates", tags=["templates"])


def _to_response(t) -> TemplateResponse:
    return TemplateResponse(
        id=t.id,
        name=t.name,
        image_name=t.image_name,
        docker_entrypoint=t.docker_entrypoint or [],
        docker_start_cmd=t.docker_start_cmd or [],
        env=t.env or {},
    )


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_200_OK)
async def create_template_route(
    body: TemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new template."""
    t = create_template(db, current_user.id, body)
    return _to_response(t)


@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List current user's templates."""
    templates = get_user_templates(db, current_user.id)
    return [_to_response(t) for t in templates]


@router.get("/{id}", response_model=TemplateResponse)
async def get_template_route(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a template by id."""
    t = get_template(db, id, current_user.id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return _to_response(t)


@router.patch("/{id}", response_model=TemplateResponse)
async def update_template_route(
    id: int,
    body: TemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a template."""
    t = update_template(db, id, current_user.id, body)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return _to_response(t)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template_route(
    id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a template."""
    if not delete_template(db, id, current_user.id):
        raise HTTPException(status_code=404, detail="Template not found")
    return None
