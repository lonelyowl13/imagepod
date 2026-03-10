from typing import Optional, List

from sqlalchemy.orm import Session, joinedload

from app.models.volume import Volume, EndpointVolume
from app.models.endpoint import Endpoint
from app.models.executor import Executor
from app.schemas.volume import VolumeCreate, VolumeUpdate
from app.utils import emit_executor_notification


@emit_executor_notification
def create_volume(db: Session, user_id: int, data: VolumeCreate) -> Volume:
    executor = db.query(Executor).filter(
        Executor.id == data.executor_id,
        Executor.user_id == user_id,
    ).first()
    if not executor:
        raise ValueError("Executor not found")
    volume = Volume(
        user_id=user_id,
        executor_id=data.executor_id,
        name=data.name,
        size_gb=data.size_gb,
    )
    db.add(volume)
    db.commit()
    db.refresh(volume)
    return volume


def get_volume(db: Session, volume_id: int, user_id: Optional[int] = None) -> Optional[Volume]:
    q = db.query(Volume).filter(Volume.id == volume_id)
    if user_id is not None:
        q = q.filter(Volume.user_id == user_id)
    return q.first()


def get_user_volumes(db: Session, user_id: int) -> List[Volume]:
    return db.query(Volume).filter(Volume.user_id == user_id).order_by(Volume.created_at.desc()).all()


def get_volumes_by_executor(db: Session, executor_id: int) -> List[Volume]:
    return db.query(Volume).filter(Volume.executor_id == executor_id).all()


@emit_executor_notification
def update_volume(db: Session, volume_id: int, user_id: int, data: VolumeUpdate) -> Optional[Volume]:
    volume = get_volume(db, volume_id, user_id)
    if not volume:
        return None
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(volume, k, v)
    db.commit()
    db.refresh(volume)
    return volume


@emit_executor_notification
def delete_volume(db: Session, volume_id: int, user_id: int) -> Optional[Volume]:
    volume = get_volume(db, volume_id, user_id)
    if not volume:
        return None
    db.delete(volume)
    db.commit()
    return volume


@emit_executor_notification
def mount_volume(
    db: Session,
    user_id: int,
    endpoint_id: int,
    volume_id: int,
    mount_path: str = "/runpod-volume",
) -> EndpointVolume:
    """Mount a volume to an endpoint. Both must belong to the same executor."""
    volume = get_volume(db, volume_id, user_id)
    if not volume:
        raise ValueError("Volume not found")
    endpoint = db.query(Endpoint).filter(
        Endpoint.id == endpoint_id,
        Endpoint.user_id == user_id,
    ).first()
    if not endpoint:
        raise ValueError("Endpoint not found")
    if endpoint.executor_id != volume.executor_id:
        raise ValueError("Volume and endpoint must be on the same executor")
    existing = db.query(EndpointVolume).filter(
        EndpointVolume.endpoint_id == endpoint_id,
        EndpointVolume.volume_id == volume_id,
    ).first()
    if existing:
        raise ValueError("Volume is already mounted to this endpoint")
    path_conflict = db.query(EndpointVolume).filter(
        EndpointVolume.endpoint_id == endpoint_id,
        EndpointVolume.mount_path == mount_path,
    ).first()
    if path_conflict:
        raise ValueError(f"Mount path '{mount_path}' is already in use on this endpoint")
    mount = EndpointVolume(
        endpoint_id=endpoint_id,
        volume_id=volume_id,
        mount_path=mount_path,
    )
    db.add(mount)
    db.commit()
    db.refresh(mount)
    return mount


@emit_executor_notification
def unmount_volume(db: Session, user_id: int, endpoint_id: int, volume_id: int) -> bool:
    """Unmount a volume from an endpoint."""
    endpoint = db.query(Endpoint).filter(
        Endpoint.id == endpoint_id,
        Endpoint.user_id == user_id,
    ).first()
    if not endpoint:
        return False
    mount = db.query(EndpointVolume).filter(
        EndpointVolume.endpoint_id == endpoint_id,
        EndpointVolume.volume_id == volume_id,
    ).first()
    if not mount:
        return False
    db.delete(mount)
    db.commit()
    return True


def get_mounts_for_endpoint(db: Session, endpoint_id: int) -> List[EndpointVolume]:
    return (
        db.query(EndpointVolume)
        .options(joinedload(EndpointVolume.volume))
        .filter(EndpointVolume.endpoint_id == endpoint_id)
        .all()
    )
