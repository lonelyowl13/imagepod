from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.models.endpoint import Endpoint
from app.models.template import Template
from app.models.executor import Executor
from app.schemas.endpoint import EndpointCreate, EndpointUpdate


def create_endpoint(db: Session, user_id: int, data: EndpointCreate) -> Endpoint:
    template = db.query(Template).filter(Template.id == data.template_id).first()
    if not template:
        raise ValueError("Template not found")
    executor = db.query(Executor).filter(Executor.id == data.executor_id).first()
    if not executor:
        raise ValueError("Executor not found")
    env = template.env.copy() if template.env else {}
    endpoint = Endpoint(
        user_id=user_id,
        name=data.name,
        template_id=data.template_id,
        executor_id=data.executor_id,
        compute_type=data.compute_type,
        execution_timeout_ms=data.execution_timeout_ms,
        idle_timeout=data.idle_timeout,
        vcpu_count=data.vcpu_count,
        env=env,
        version=0,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint


def get_endpoint(db: Session, endpoint_id: int, user_id: Optional[int] = None) -> Optional[Endpoint]:
    query = (
        db.query(Endpoint)
        .options(joinedload(Endpoint.template), joinedload(Endpoint.executor))
        .filter(Endpoint.id == endpoint_id)
    )
    if user_id is not None:
        query = query.filter(Endpoint.user_id == user_id)
    return query.first()


def get_user_endpoints(db: Session, user_id: int) -> List[Endpoint]:
    return (
        db.query(Endpoint)
        .options(joinedload(Endpoint.template), joinedload(Endpoint.executor))
        .filter(Endpoint.user_id == user_id)
        .order_by(desc(Endpoint.created_at))
        .all()
    )


def update_endpoint(
    db: Session, endpoint_id: int, data: EndpointUpdate, user_id: int
) -> Optional[Endpoint]:
    endpoint = get_endpoint(db, endpoint_id, user_id)
    if not endpoint:
        return None
    if data.template_id is not None:
        template = db.query(Template).filter(Template.id == data.template_id).first()
        if not template:
            raise ValueError("Template not found")
    if data.executor_id is not None:
        executor = db.query(Executor).filter(Executor.id == data.executor_id).first()
        if not executor:
            raise ValueError("Executor not found")
    payload = data.model_dump(exclude_unset=True, by_alias=False)

    endpoint.version += 1

    for k, v in payload.items():
        setattr(endpoint, k, v)
    db.commit()
    db.refresh(endpoint)
    return endpoint


def delete_endpoint(db: Session, endpoint_id: int, user_id: int) -> bool:
    endpoint = get_endpoint(db, endpoint_id, user_id)
    if not endpoint:
        return False
    db.delete(endpoint)
    db.commit()
    return True


def update_endpoint_status_by_executor(
    db: Session, endpoint_id: int, executor_id: int, status: str
) -> Optional[Endpoint]:
    """Update endpoint status; only allowed if endpoint belongs to this executor."""
    endpoint = db.query(Endpoint).filter(
        Endpoint.id == endpoint_id,
        Endpoint.executor_id == executor_id,
    ).first()
    if not endpoint:
        return None
    endpoint.status = status
    db.commit()
    db.refresh(endpoint)
    return endpoint
