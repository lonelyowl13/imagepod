from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.models.endpoint import Endpoint
from app.models.template import Template
from app.models.executor import Executor
from app.schemas.endpoint import EndpointCreate, EndpointUpdate
import secrets
import string


class EndpointService:
    def __init__(self, db: Session):
        self.db = db

    def create_endpoint(self, user_id: int, endpoint_data: EndpointCreate) -> Endpoint:
        """Create a new endpoint from a template"""
        # Validate template exists
        template = self.db.query(Template).filter(
            Template.template_id == endpoint_data.template_id
        ).first()
        if not template:
            raise ValueError("Template not found")
        
        # Validate executor exists
        executor = self.db.query(Executor).filter(
            Executor.id == endpoint_data.executor_id
        ).first()
        if not executor:
            raise ValueError("Executor not found")
        
        # Generate endpoint ID (15 character alphanumeric, like RunPod)
        endpoint_id = self._generate_endpoint_id()
        
        # Merge template env with any endpoint-specific env (endpoint env takes precedence)
        env = template.env.copy() if template.env else {}
        # For now, we'll use template env. Later, endpoint_data could have env overrides
        
        db_endpoint = Endpoint(
            user_id=user_id,
            endpoint_id=endpoint_id,
            name=endpoint_data.name,
            template_id=endpoint_data.template_id,
            executor_id=endpoint_data.executor_id,
            allowed_cuda_versions=endpoint_data.allowed_cuda_versions,
            compute_type=endpoint_data.compute_type,
            execution_timeout_ms=endpoint_data.execution_timeout_ms,
            idle_timeout=endpoint_data.idle_timeout,
            vcpu_count=endpoint_data.vcpu_count,
            env=env,
            version=0
        )

        self.db.add(db_endpoint)
        self.db.commit()
        self.db.refresh(db_endpoint)
        return db_endpoint

    def get_endpoint(self, endpoint_id: str, user_id: Optional[int] = None) -> Optional[Endpoint]:
        """Get endpoint by endpoint_id"""
        query = (
            self.db.query(Endpoint)
            .options(joinedload(Endpoint.template), joinedload(Endpoint.executor))
            .filter(Endpoint.endpoint_id == endpoint_id)
        )
        if user_id:
            query = query.filter(Endpoint.user_id == user_id)
        return query.first()

    def get_user_endpoints(self, user_id: int) -> List[Endpoint]:
        """Get all endpoints for a user"""
        return (
            self.db.query(Endpoint)
            .options(joinedload(Endpoint.template), joinedload(Endpoint.executor))
            .filter(Endpoint.user_id == user_id)
            .order_by(desc(Endpoint.created_at))
            .all()
        )

    def update_endpoint(self, endpoint_id: str, endpoint_update: EndpointUpdate, user_id: int) -> Optional[Endpoint]:
        """Update an endpoint"""
        endpoint = self.get_endpoint(endpoint_id, user_id)
        if not endpoint:
            return None

        # Validate template if being updated
        if endpoint_update.template_id:
            template = self.db.query(Template).filter(
                Template.template_id == endpoint_update.template_id
            ).first()
            if not template:
                raise ValueError("Template not found")
        
        # Validate executor if being updated
        if endpoint_update.executor_id:
            executor = self.db.query(Executor).filter(
                Executor.id == endpoint_update.executor_id
            ).first()
            if not executor:
                raise ValueError("Executor not found")

        # Use model_dump with by_alias=False to get snake_case field names
        update_data = endpoint_update.model_dump(exclude_unset=True, by_alias=False)
        
        # Increment version on update
        if update_data:
            endpoint.version += 1
        
        for field, value in update_data.items():
            setattr(endpoint, field, value)

        self.db.commit()
        self.db.refresh(endpoint)
        return endpoint

    def delete_endpoint(self, endpoint_id: str, user_id: int) -> bool:
        """Delete an endpoint"""
        endpoint = self.get_endpoint(endpoint_id, user_id)
        if not endpoint:
            return False

        self.db.delete(endpoint)
        self.db.commit()
        return True

    def _generate_endpoint_id(self) -> str:
        """Generate a unique endpoint ID (15 character alphanumeric, like RunPod)"""
        alphabet = string.ascii_lowercase + string.digits
        while True:
            endpoint_id = ''.join(secrets.choice(alphabet) for _ in range(15))
            # Check if it already exists
            if not self.db.query(Endpoint).filter(Endpoint.endpoint_id == endpoint_id).first():
                return endpoint_id
