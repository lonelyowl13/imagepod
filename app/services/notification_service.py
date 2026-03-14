from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.enums import NotificationType, EntityKind
from app.models.executor_notification import ExecutorNotification


def create_notification(
    db: Session,
    executor_id: int,
    type: NotificationType,
    entity_kind: EntityKind,
    entity_id: int,
    payload: Dict[str, Any],
) -> ExecutorNotification:
    notification = ExecutorNotification(
        executor_id=executor_id,
        type=type.value,
        entity_kind=entity_kind.value,
        entity_id=entity_id,
        payload=payload,
        acknowledged=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_pending_notifications(db: Session, executor_id: int) -> List[ExecutorNotification]:
    return (
        db.query(ExecutorNotification)
        .filter(
            ExecutorNotification.executor_id == executor_id,
            ExecutorNotification.acknowledged.is_(False),
        )
        .order_by(ExecutorNotification.created_at.asc())
        .all()
    )


def acknowledge_notifications(
    db: Session,
    executor_id: int,
    notification_ids: List[int],
) -> int:
    if not notification_ids:
        return 0
    q = db.query(ExecutorNotification).filter(
        ExecutorNotification.executor_id == executor_id,
        ExecutorNotification.id.in_(notification_ids),
    )
    updated = q.update({ExecutorNotification.acknowledged: True}, synchronize_session="fetch")
    db.commit()
    return updated

