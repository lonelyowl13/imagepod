from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.auth import get_current_active_user, get_current_superuser
from app.models.user import User
from app.schemas.worker import (
    WorkerCreate, WorkerResponse, WorkerPoolCreate, WorkerPoolResponse, WorkerStatusUpdate
)
from app.services.worker_service import WorkerService

router = APIRouter(prefix="/workers", tags=["workers"])


@router.post("/pools/", response_model=WorkerPoolResponse)
async def create_worker_pool(
    pool_data: WorkerPoolCreate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Create a new worker pool (admin only)"""
    worker_service = WorkerService(db)
    
    try:
        pool = worker_service.create_worker_pool(pool_data)
        return pool
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pools/", response_model=List[WorkerPoolResponse])
async def get_worker_pools(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get worker pools"""
    worker_service = WorkerService(db)
    pools = worker_service.get_worker_pools(skip, limit)
    return pools


@router.get("/pools/{pool_id}", response_model=WorkerPoolResponse)
async def get_worker_pool(
    pool_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific worker pool"""
    worker_service = WorkerService(db)
    pool = worker_service.get_worker_pool(pool_id)
    
    if not pool:
        raise HTTPException(status_code=404, detail="Worker pool not found")
    
    return pool


@router.put("/pools/{pool_id}/scale")
async def scale_worker_pool(
    pool_id: int,
    target_workers: int = Query(..., ge=0),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Scale a worker pool (admin only)"""
    worker_service = WorkerService(db)
    success = worker_service.scale_pool(pool_id, target_workers)
    
    if not success:
        raise HTTPException(status_code=404, detail="Worker pool not found")
    
    return {"message": f"Worker pool scaled to {target_workers} workers"}


@router.delete("/pools/{pool_id}")
async def delete_worker_pool(
    pool_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Delete a worker pool (admin only)"""
    worker_service = WorkerService(db)
    success = worker_service.delete_worker_pool(pool_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Worker pool not found")
    
    return {"message": "Worker pool deleted successfully"}


@router.post("/pools/{pool_id}/workers/", response_model=WorkerResponse)
async def create_worker(
    pool_id: int,
    worker_data: WorkerCreate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Create a new worker (admin only)"""
    worker_service = WorkerService(db)
    
    try:
        worker = worker_service.create_worker(pool_id, worker_data)
        return worker
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[WorkerResponse])
async def get_workers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all workers"""
    worker_service = WorkerService(db)
    workers = worker_service.get_workers(skip, limit)
    return workers


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific worker"""
    worker_service = WorkerService(db)
    worker = worker_service.get_worker(worker_id)
    
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    return worker


@router.put("/{worker_id}/status")
async def update_worker_status(
    worker_id: int,
    status_update: WorkerStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update worker status (used by workers for heartbeats)"""
    worker_service = WorkerService(db)
    worker = worker_service.update_worker_status(worker_id, status_update)
    
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    return worker


@router.delete("/{worker_id}")
async def terminate_worker(
    worker_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Terminate a worker (admin only)"""
    worker_service = WorkerService(db)
    success = worker_service.terminate_worker(worker_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    return {"message": "Worker terminated successfully"}


@router.post("/auto-scale")
async def trigger_auto_scale(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Trigger auto-scaling for all worker pools (admin only)"""
    worker_service = WorkerService(db)
    worker_service.auto_scale_pools()
    
    return {"message": "Auto-scaling triggered successfully"}


@router.post("/health-check")
async def trigger_health_check(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Trigger health check for all workers (admin only)"""
    worker_service = WorkerService(db)
    await worker_service.health_check_workers()
    
    return {"message": "Health check completed successfully"}
