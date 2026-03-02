from typing import Optional, List, Tuple

from sqlalchemy.orm import Session, joinedload
from app.enums import JobStatus
from app.models.executor import Executor
from app.models.job import Job
from app.models.endpoint import Endpoint
from app.models.volume import EndpointVolume
from app.utils import hash_key, generate_api_key


def create_executor_with_key(db: Session, user_id: int, name: str) -> Optional[Tuple[Executor, str]]:
    """Create executor and return (executor, raw_api_key)."""
    raw_key = generate_api_key()
    key_hash = hash_key(raw_key)
    executor = Executor(name=name, token_hash=key_hash, user_id=user_id)
    db.add(executor)
    db.commit()
    db.refresh(executor)
    return (executor, raw_key)


def get_executor_by_api_key(db: Session, api_key: str) -> Optional[Executor]:
    key_hash = hash_key(api_key)
    return db.query(Executor).filter(Executor.token_hash == key_hash).first()


def update_executor_spec(
    db: Session,
    executor_id: int,
    *,
    gpu: Optional[str] = None,
    vram: Optional[int] = None,
    cpu: Optional[str] = None,
    ram: Optional[int] = None,
    compute_type: Optional[str] = None,
    cuda_version: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[Executor]:
    executor = db.query(Executor).filter(Executor.id == executor_id).first()
    if not executor:
        return None
    if gpu is not None:
        executor.gpu = gpu
    if vram is not None:
        executor.vram = vram
    if cpu is not None:
        executor.cpu = cpu
    if ram is not None:
        executor.ram = ram
    if compute_type is not None:
        executor.compute_type = compute_type
    if cuda_version is not None:
        executor.cuda_version = cuda_version
    if metadata is not None:
        executor.metadata_ = metadata
    db.commit()
    db.refresh(executor)
    return executor


def get_jobs_in_queue(db: Session, executor_id: int) -> List[Job]:
    return (
        db.query(Job)
        .filter(Job.executor_id == executor_id, Job.status == JobStatus.IN_QUEUE)
        .all()
    )


def update_job_for_executor(
    db: Session,
    executor_id: int,
    job_id: int,
    *,
    status: Optional[str] = None,
    delay_time: Optional[int] = None,
    execution_time: Optional[int] = None,
    output_data: Optional[dict] = None,
) -> Optional[Job]:
    job = db.query(Job).filter(Job.id == job_id, Job.executor_id == executor_id).first()
    if not job:
        return None
    if status is not None:
        job.status = status
    if delay_time is not None:
        job.delay_time = delay_time
    if execution_time is not None:
        job.execution_time = execution_time
    if output_data is not None:
        job.output_data = output_data
    db.commit()
    db.refresh(job)
    return job


def get_endpoints_for_executor(db: Session, executor_id: int) -> List[Endpoint]:
    return db.query(Endpoint).filter(Endpoint.executor_id == executor_id).all()


def get_endpoints_for_executor_by_status(
    db: Session, executor_id: int, status: str
) -> List[Endpoint]:
    """Return endpoints for this executor with the given status (e.g. 'Deploying'), with template and volumes loaded."""
    return (
        db.query(Endpoint)
        .options(
            joinedload(Endpoint.template),
            joinedload(Endpoint.volume_mounts).joinedload(EndpointVolume.volume),
        )
        .filter(Endpoint.executor_id == executor_id, Endpoint.status == status)
        .all()
    )


def get_endpoints_by_ids(
    db: Session, executor_id: int, endpoint_ids: List[int]
) -> List[Endpoint]:
    """Return endpoints for this executor with the given ids, with template and volumes loaded."""
    if not endpoint_ids:
        return []
    return (
        db.query(Endpoint)
        .options(
            joinedload(Endpoint.template),
            joinedload(Endpoint.volume_mounts).joinedload(EndpointVolume.volume),
        )
        .filter(
            Endpoint.executor_id == executor_id,
            Endpoint.id.in_(endpoint_ids),
        )
        .all()
    )


def get_executors_for_user(db: Session, user_id: int) -> List[Executor]:
    """Return all executors owned by the given user."""
    return db.query(Executor).filter(Executor.user_id == user_id).all()
