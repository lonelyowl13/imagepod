from typing import Any, Dict
from datetime import datetime

from pydantic import BaseModel

from app.enums import NotificationType, EntityKind


class Notification(BaseModel):
    id: int
    type: NotificationType
    entity_kind: EntityKind
    entity_id: int
    executor_id: int
    payload: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True

