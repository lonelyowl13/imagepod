from functools import wraps
import hashlib
import secrets
import string
from typing import Any, Callable

from sqlalchemy.orm import Session


from app.enums import EntityKind, NotificationType
from app.models import Endpoint, Job, Pod, Volume
from app.schemas import EndpointResponse, JobResponse, PodResponse
from app.schemas.volume import VolumeResponse
from app.services.notification_service import create_notification


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def emit_executor_notification(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to emit executor notification when an entity is created or updated"""

    @wraps(func)
    def wrapper(db: Session, *args, **kwargs):
        entity = func(db, *args, **kwargs)

        if isinstance(entity, Endpoint):
            type = NotificationType.ENDPOINT_CHANGED
            entity_kind = EntityKind.ENDPOINT
            payload = EndpointResponse.model_validate(entity, from_attributes=True).model_dump(mode="json")
        elif isinstance(entity, Job):
            type = NotificationType.JOB_CHANGED
            entity_kind = EntityKind.JOB
            payload = JobResponse.model_validate(entity, from_attributes=True).model_dump(mode="json")
        elif isinstance(entity, Pod):
            type = NotificationType.POD_STATUS_CHANGED
            entity_kind = EntityKind.POD
            payload = PodResponse.model_validate(entity, from_attributes=True).model_dump(mode="json")
        elif isinstance(entity, Volume):
            type = NotificationType.VOLUME_CHANGED
            entity_kind = EntityKind.VOLUME
            payload = VolumeResponse.model_validate(entity, from_attributes=True).model_dump(mode="json")
        else:
            raise ValueError(f"Unsupported entity type: {type(entity)}")

        create_notification(db, entity.executor_id, type, entity_kind, entity.id, payload)
        return entity

    return wrapper
