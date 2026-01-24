from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateUpdate
import uuid
import secrets
import string


class TemplateService:
    def __init__(self, db: Session):
        self.db = db

    def create_template(self, user_id: int, template_data: TemplateCreate) -> Template:
        """Create a new template"""
        # Generate template ID (10 character alphanumeric, like RunPod)
        template_id = self._generate_template_id()
        
        db_template = Template(
            user_id=user_id,
            template_id=template_id,
            name=template_data.name,
            image_name=template_data.image_name,
            category=template_data.category,
            container_disk_in_gb=template_data.container_disk_in_gb,
            container_registry_auth_id=template_data.container_registry_auth_id,
            docker_entrypoint=template_data.docker_entrypoint,
            docker_start_cmd=template_data.docker_start_cmd,
            env=template_data.env,
            ports=template_data.ports,
            readme=template_data.readme,
            volume_in_gb=template_data.volume_in_gb,
            volume_mount_path=template_data.volume_mount_path,
            is_public=template_data.is_public,
            is_serverless=template_data.is_serverless,
            is_runpod=False  # User-created templates are not RunPod templates
        )

        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        return db_template

    def get_template(self, template_id: str, user_id: Optional[int] = None) -> Optional[Template]:
        """Get template by template_id"""
        query = self.db.query(Template).filter(Template.template_id == template_id)
        if user_id:
            query = query.filter(Template.user_id == user_id)
        return query.first()

    def get_user_templates(self, user_id: int) -> List[Template]:
        """Get all templates for a user"""
        return (
            self.db.query(Template)
            .filter(Template.user_id == user_id)
            .order_by(desc(Template.created_at))
            .all()
        )

    def update_template(self, template_id: str, template_update: TemplateUpdate, user_id: int) -> Optional[Template]:
        """Update a template"""
        template = self.get_template(template_id, user_id)
        if not template:
            return None

        # Use model_dump with by_alias=False to get snake_case field names
        update_data = template_update.model_dump(exclude_unset=True, by_alias=False)
        for field, value in update_data.items():
            setattr(template, field, value)

        self.db.commit()
        self.db.refresh(template)
        return template

    def delete_template(self, template_id: str, user_id: int) -> bool:
        """Delete a template"""
        template = self.get_template(template_id, user_id)
        if not template:
            return False

        self.db.delete(template)
        self.db.commit()
        return True

    def _generate_template_id(self) -> str:
        """Generate a unique template ID (10 character alphanumeric, like RunPod)"""
        # Generate a 10-character alphanumeric ID
        alphabet = string.ascii_lowercase + string.digits
        while True:
            template_id = ''.join(secrets.choice(alphabet) for _ in range(10))
            # Check if it already exists
            if not self.db.query(Template).filter(Template.template_id == template_id).first():
                return template_id

