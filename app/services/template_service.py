from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateUpdate


def create_template(db: Session, user_id: int, data: TemplateCreate) -> Template:
    t = Template(
        user_id=user_id,
        name=data.name,
        image_name=data.image_name,
        docker_entrypoint=data.docker_entrypoint or [],
        docker_start_cmd=data.docker_start_cmd or [],
        env=data.env or {},
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def get_template(db: Session, template_id: int, user_id: Optional[int] = None) -> Optional[Template]:
    q = db.query(Template).filter(Template.id == template_id)
    if user_id is not None:
        q = q.filter(Template.user_id == user_id)
    return q.first()


def get_user_templates(db: Session, user_id: int) -> List[Template]:
    return (
        db.query(Template)
        .filter(Template.user_id == user_id)
        .order_by(desc(Template.created_at))
        .all()
    )


def update_template(
    db: Session, template_id: int, user_id: int, data: TemplateUpdate
) -> Optional[Template]:
    t = get_template(db, template_id, user_id)
    if not t:
        return None
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


def delete_template(db: Session, template_id: int, user_id: int) -> bool:
    t = get_template(db, template_id, user_id)
    if not t:
        return False
    db.delete(t)
    db.commit()
    return True
