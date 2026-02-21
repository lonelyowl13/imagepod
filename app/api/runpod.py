from typing import List, Optional

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.helpers import get_current_executor
from app.models.executor import Executor
from app.models.endpoint import Endpoint
from app.models.job import Job
from app.services.executor_service import update_job_for_executor
from app.redis_client import get_redis


def _stream_key(job_id: int) -> str:
    return f"job:{job_id}:stream"


router = APIRouter(prefix="/runpod", tags=["runpod"])


def _get_endpoint_for_pod(
    db: Session, pod_id: int, executor: Executor
) -> Endpoint:
    """
    Resolve a RunPod worker / pod id to an Endpoint that belongs to the
    authenticated executor. For now we use pod_id == endpoint.id.
    """
    endpoint = (
        db.query(Endpoint)
        .filter(Endpoint.id == pod_id, Endpoint.executor_id == executor.id)
        .first()
    )
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found for this pod or executor",
        )
    return endpoint


def _serialize_job_for_runpod(job: Job) -> dict:
    """
    Shape a Job instance into the minimal JSON that the RunPod SDK
    expects from its job-take endpoint.
    """
    return {
        "id": str(job.id),
        "input": job.input_data or {},
    }


@router.get("/job-take/{pod_id}")
async def job_take_single(
    pod_id: int,
    request: Request,
    batch_size: Optional[int] = None,
    job_in_progress: Optional[str] = "0",
    executor: Executor = Depends(get_current_executor),
    db: Session = Depends(get_db),
):
    """
    RunPod-compatible single job-take endpoint.

    The RunPod SDK calls RUNPOD_WEBHOOK_GET_JOB (with $ID already substituted
    for the worker id), and this handler returns either:
      - 204 No Content when there is no work
      - A JSON object with at least {id, input} describing the job
    """
    # If the SDK requested batch mode, delegate to the batch handler.
    if batch_size and batch_size > 1:
        return await job_take_batch(
            pod_id=pod_id,
            request=request,
            batch_size=batch_size,
            job_in_progress=job_in_progress,
            executor=executor,
            db=db,
        )

    _ = job_in_progress  # Currently unused but accepted for compatibility.

    endpoint = _get_endpoint_for_pod(db, pod_id, executor)

    job = (
        db.query(Job)
        .filter(
            Job.endpoint_id == endpoint.id,
            Job.executor_id == executor.id,
            Job.status == "IN_QUEUE",
        )
        .order_by(Job.id.asc())
        .first()
    )

    if not job:
        # RunPod expects 204 when there is no work.
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Mark job as RUNNING as soon as it is handed to the worker.
    job.status = "RUNNING"
    db.commit()
    db.refresh(job)

    return _serialize_job_for_runpod(job)


@router.get("/job-take-batch/{pod_id}")
async def job_take_batch(
    pod_id: int,
    request: Request,
    batch_size: int = 1,
    job_in_progress: Optional[str] = "0",
    executor: Executor = Depends(get_current_executor),
    db: Session = Depends(get_db),
):
    """
    RunPod-compatible batch job-take endpoint.
    """
    _ = job_in_progress  # Currently unused but accepted for compatibility.

    endpoint = _get_endpoint_for_pod(db, pod_id, executor)

    limit = max(1, batch_size)

    jobs: List[Job] = (
        db.query(Job)
        .filter(
            Job.endpoint_id == endpoint.id,
            Job.executor_id == executor.id,
            Job.status == "IN_QUEUE",
        )
        .order_by(Job.id.asc())
        .limit(limit)
        .all()
    )

    if not jobs:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Mark all as RUNNING.
    for job in jobs:
        job.status = "RUNNING"
    db.commit()

    return [_serialize_job_for_runpod(job) for job in jobs]


@router.post("/job-done/{pod_id}")
async def job_done(
    pod_id: int,
    request: Request,
    isStream: Optional[str] = "false",
    job_id: Optional[str] = None,
    executor: Executor = Depends(get_current_executor),
    db: Session = Depends(get_db),
):
    """
    RunPod-compatible job completion endpoint.

    The RunPod SDK POSTs a JSON body (sent as form-urlencoded data) with:
      - output: arbitrary JSON-serializable data
      - error: optional error payload
      - stopPod: optional boolean flag
    """
    _ = isStream  # We currently don't differentiate streaming vs final here.

    raw_body = await request.body()
    try:
        job_data = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job result payload",
        )

    if not job_id:
        # The SDK always appends job_id in the query string; require it.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing job_id in query parameters",
        )

    # Ensure the endpoint exists and belongs to this executor.
    endpoint = _get_endpoint_for_pod(db, pod_id, executor)

    # Resolve the job and update it using the existing executor service.
    try:
        job_id_int = int(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job_id",
        )

    status_value = "COMPLETED"
    if "error" in job_data and job_data["error"]:
        status_value = "FAILED"

    output_data = job_data.get("output")

    job = update_job_for_executor(
        db,
        executor_id=executor.id,
        job_id=job_id_int,
        status=status_value,
        output_data=output_data,
    )

    if not job or job.endpoint_id != endpoint.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found for this endpoint/executor",
        )

    r = get_redis()
    stream_key = _stream_key(job_id_int)
    if r.exists(stream_key):
        r.expire(stream_key, 300)

    return {"detail": "ok", "id": job.id, "status": job.status}


@router.post("/job-stream/{pod_id}")
async def job_stream(
    pod_id: int,
    request: Request,
    job_id: Optional[str] = None,
    executor: Executor = Depends(get_current_executor),
    db: Session = Depends(get_db),
):
    """
    RunPod-compatible streaming results endpoint.

    The RunPod SDK POSTs a JSON body with {"output": <chunk>} for each
    intermediate result. Chunks are buffered in Redis so clients can poll
    for accumulated stream data via the job status endpoint.
    """
    if not job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing job_id in query parameters",
        )

    raw_body = await request.body()
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stream payload",
        )

    endpoint = _get_endpoint_for_pod(db, pod_id, executor)

    try:
        job_id_int = int(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job_id",
        )

    job = (
        db.query(Job)
        .filter(
            Job.id == job_id_int,
            Job.executor_id == executor.id,
            Job.endpoint_id == endpoint.id,
        )
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found for this endpoint/executor",
        )

    chunk = body.get("output")
    r = get_redis()
    r.rpush(_stream_key(job_id_int), json.dumps(chunk))

    return {"detail": "ok"}


@router.get("/ping/{pod_id}")
async def ping(
    pod_id: int,
    job_id: Optional[str] = None,
    runpod_version: Optional[str] = None,
    executor: Executor = Depends(get_current_executor),
    db: Session = Depends(get_db),
):
    """
    RunPod-compatible heartbeat endpoint.

    Updates the executor's last_heartbeat and returns a simple OK response.
    """
    _ = job_id, runpod_version  # Currently unused.

    # Ensure the endpoint exists and belongs to this executor.
    _ = _get_endpoint_for_pod(db, pod_id, executor)

    executor.last_heartbeat = datetime.now(timezone.utc)
    db.commit()

    return {"status": "ok"}

