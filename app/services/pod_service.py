from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.enums import PodStatus
from app.models.pod import Pod
from app.models.template import Template
from app.models.executor import Executor, ExecutorShare
from app.schemas.pod import PodCreate, PodUpdate
from sqlalchemy.sql import func

from app.utils import emit_executor_notification


def _user_can_use_executor(db: Session, executor: Executor, user_id: int) -> bool:
    if executor.user_id == user_id:
        return True
    return (
        db.query(ExecutorShare)
        .filter(
            ExecutorShare.executor_id == executor.id,
            ExecutorShare.user_id == user_id,
        )
        .first()
        is not None
    )


def _build_env(template_env: Optional[Dict[str, Any]], override_env: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = template_env.copy() if template_env else {}
    if override_env:
        base.update(override_env)
    return base


@emit_executor_notification
def create_pod(db: Session, user_id: int, data: PodCreate) -> Pod:
    template = db.query(Template).filter(Template.id == data.template_id).first()
    if not template:
        raise ValueError("Template not found")
    if getattr(template, "is_serverless", True):
        raise ValueError("Template is not a pod template")

    executor = db.query(Executor).filter(Executor.id == data.executor_id).first()
    if not executor:
        raise ValueError("Executor not found")
    if not _user_can_use_executor(db, executor, user_id):
        raise ValueError("Executor not found")

    env = _build_env(template.env, data.env)

    pod = Pod(
        user_id=user_id,
        name=data.name,
        template_id=data.template_id,
        executor_id=data.executor_id,
        compute_type=data.compute_type,
        vcpu_count=data.vcpu_count,
        env=env,
        ports=data.ports,
        status=PodStatus.STOPPED,
    )
    db.add(pod)
    db.commit()
    db.refresh(pod)
    return pod


def get_pod(db: Session, pod_id: int, user_id: Optional[int] = None) -> Optional[Pod]:
    query = (
        db.query(Pod)
        .options(
            joinedload(Pod.template),
            joinedload(Pod.executor),
        )
        .filter(Pod.id == pod_id)
    )
    if user_id is not None:
        query = query.filter(Pod.user_id == user_id)
    return query.first()


def get_user_pods(db: Session, user_id: int) -> List[Pod]:
    return (
        db.query(Pod)
        .options(
            joinedload(Pod.template),
            joinedload(Pod.executor),
        )
        .filter(Pod.user_id == user_id)
        .order_by(desc(Pod.created_at))
        .all()
    )


@emit_executor_notification
def update_pod(
    db: Session, pod_id: int, data: PodUpdate, user_id: int
) -> Optional[Pod]:
    pod = get_pod(db, pod_id, user_id)
    if not pod:
        return None

    if data.template_id is not None:
        template = db.query(Template).filter(Template.id == data.template_id).first()
        if not template:
            raise ValueError("Template not found")
        if getattr(template, "is_serverless", True):
            raise ValueError("Template is not a pod template")

    if data.executor_id is not None:
        executor = db.query(Executor).filter(Executor.id == data.executor_id).first()
        if not executor:
            raise ValueError("Executor not found")
        if not _user_can_use_executor(db, executor, user_id):
            raise ValueError("Executor not found")

    payload = data.model_dump(exclude_unset=True)

    # Handle env merging if provided
    env_override = payload.pop("env", None)
    if env_override is not None:
        pod.env = _build_env(pod.env, env_override)

    for k, v in payload.items():
        setattr(pod, k, v)

    db.commit()
    db.refresh(pod)
    return pod


@emit_executor_notification
def delete_pod(db: Session, pod_id: int, user_id: int) -> Optional[Pod]:
    pod = get_pod(db, pod_id, user_id)
    if not pod:
        return None
    db.delete(pod)
    db.commit()
    return True


@emit_executor_notification
def start_pod(db: Session, pod_id: int, user_id: int) -> Optional[Pod]:
    pod = get_pod(db, pod_id, user_id)
    if not pod:
        return None
    if pod.status == PodStatus.TERMINATED:
        raise ValueError("Pod is terminated and cannot be started")
    if pod.status == PodStatus.RUNNING:
        return pod

    pod.status = PodStatus.RUNNING
    pod.last_started_at = func.now()
    db.commit()
    db.refresh(pod)
    return pod


@emit_executor_notification
def stop_pod(db: Session, pod_id: int, user_id: int) -> Optional[Pod]:
    pod = get_pod(db, pod_id, user_id)
    if not pod:
        return None
    if pod.status != PodStatus.RUNNING:
        return pod

    pod.status = PodStatus.STOPPED
    pod.last_stopped_at = func.now()
    db.commit()
    db.refresh(pod)
    return pod


@emit_executor_notification
def mark_pod_terminated(
    db: Session, pod_id: int, executor_id: int
) -> Optional[Pod]:
    pod = (
        db.query(Pod)
        .filter(
            Pod.id == pod_id,
            Pod.executor_id == executor_id,
        )
        .first()
    )
    if not pod:
        return None
    pod.status = PodStatus.TERMINATED
    db.commit()
    db.refresh(pod)
    return pod

