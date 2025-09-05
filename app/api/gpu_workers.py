from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.services.gpu_worker_service import GPUWorkerService
from app.schemas.gpu_worker import (
    GPUNodeRegistration, GPUNodeResponse, GPUNodeUpdate, GPUJobCreate, GPUJobResponse,
    GPUJobUpdate, WorkerAgentRegistration, WorkerAgentResponse, WorkerAgentUpdate,
    NodeHeartbeat, JobSubmission, JobStatusUpdate, NodeStats
)
from app.auth import get_current_active_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gpu-workers", tags=["GPU Workers"])


@router.post("/nodes/register", response_model=GPUNodeResponse)
async def register_gpu_node(
    node_data: GPUNodeRegistration,
    db: Session = Depends(get_db)
):
    """Register a new GPU node"""
    try:
        gpu_service = GPUWorkerService(db)
        node = gpu_service.register_gpu_node(node_data)
        return node
    except Exception as e:
        logger.error(f"Failed to register GPU node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register GPU node: {str(e)}"
        )


@router.get("/nodes/", response_model=List[GPUNodeResponse])
async def list_gpu_nodes(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List GPU nodes"""
    try:
        gpu_service = GPUWorkerService(db)
        query = gpu_service.db.query(gpu_service.db.query(GPUNode).filter())
        
        if status:
            query = query.filter(GPUNode.status == status)
        
        nodes = query.offset(skip).limit(limit).all()
        return nodes
    except Exception as e:
        logger.error(f"Failed to list GPU nodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list GPU nodes: {str(e)}"
        )


@router.get("/nodes/{node_id}", response_model=GPUNodeResponse)
async def get_gpu_node(
    node_id: str,
    db: Session = Depends(get_db)
):
    """Get GPU node by ID"""
    try:
        gpu_service = GPUWorkerService(db)
        node = gpu_service.get_gpu_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GPU node not found"
            )
        return node
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get GPU node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get GPU node: {str(e)}"
        )


@router.put("/nodes/{node_id}", response_model=GPUNodeResponse)
async def update_gpu_node(
    node_id: str,
    node_update: GPUNodeUpdate,
    db: Session = Depends(get_db)
):
    """Update GPU node"""
    try:
        gpu_service = GPUWorkerService(db)
        node = gpu_service.get_gpu_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GPU node not found"
            )
        
        # Update node fields
        for field, value in node_update.dict(exclude_unset=True).items():
            setattr(node, field, value)
        
        db.commit()
        db.refresh(node)
        return node
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update GPU node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update GPU node: {str(e)}"
        )


@router.post("/nodes/{node_id}/heartbeat", response_model=GPUNodeResponse)
async def update_node_heartbeat(
    node_id: str,
    heartbeat_data: NodeHeartbeat,
    db: Session = Depends(get_db)
):
    """Update node heartbeat"""
    try:
        gpu_service = GPUWorkerService(db)
        node = gpu_service.update_node_heartbeat(node_id, heartbeat_data)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GPU node not found"
            )
        return node
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update node heartbeat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update node heartbeat: {str(e)}"
        )


@router.get("/nodes/{node_id}/stats", response_model=NodeStats)
async def get_node_stats(
    node_id: str,
    db: Session = Depends(get_db)
):
    """Get node statistics"""
    try:
        gpu_service = GPUWorkerService(db)
        stats = gpu_service.get_node_stats(node_id)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GPU node not found"
            )
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get node stats: {str(e)}"
        )


@router.post("/agents/register", response_model=WorkerAgentResponse)
async def register_worker_agent(
    agent_data: WorkerAgentRegistration,
    db: Session = Depends(get_db)
):
    """Register a worker agent"""
    try:
        gpu_service = GPUWorkerService(db)
        agent = gpu_service.register_worker_agent(agent_data)
        return agent
    except Exception as e:
        logger.error(f"Failed to register worker agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register worker agent: {str(e)}"
        )


@router.get("/agents/", response_model=List[WorkerAgentResponse])
async def list_worker_agents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List worker agents"""
    try:
        gpu_service = GPUWorkerService(db)
        query = gpu_service.db.query(WorkerAgent)
        
        if status:
            query = query.filter(WorkerAgent.status == status)
        
        agents = query.offset(skip).limit(limit).all()
        return agents
    except Exception as e:
        logger.error(f"Failed to list worker agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list worker agents: {str(e)}"
        )


@router.get("/agents/{agent_id}", response_model=WorkerAgentResponse)
async def get_worker_agent(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """Get worker agent by ID"""
    try:
        gpu_service = GPUWorkerService(db)
        agent = gpu_service.db.query(WorkerAgent).filter(
            WorkerAgent.agent_id == agent_id
        ).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Worker agent not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get worker agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get worker agent: {str(e)}"
        )


@router.put("/agents/{agent_id}", response_model=WorkerAgentResponse)
async def update_worker_agent(
    agent_id: str,
    agent_update: WorkerAgentUpdate,
    db: Session = Depends(get_db)
):
    """Update worker agent"""
    try:
        gpu_service = GPUWorkerService(db)
        agent = gpu_service.db.query(WorkerAgent).filter(
            WorkerAgent.agent_id == agent_id
        ).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Worker agent not found"
            )
        
        # Update agent fields
        for field, value in agent_update.dict(exclude_unset=True).items():
            setattr(agent, field, value)
        
        db.commit()
        db.refresh(agent)
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update worker agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update worker agent: {str(e)}"
        )


@router.post("/jobs/", response_model=GPUJobResponse)
async def create_gpu_job(
    job_data: GPUJobCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new GPU job"""
    try:
        gpu_service = GPUWorkerService(db)
        job = gpu_service.create_gpu_job(current_user.id, job_data)
        return job
    except Exception as e:
        logger.error(f"Failed to create GPU job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create GPU job: {str(e)}"
        )


@router.get("/jobs/", response_model=List[GPUJobResponse])
async def list_gpu_jobs(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List GPU jobs for current user"""
    try:
        gpu_service = GPUWorkerService(db)
        query = gpu_service.db.query(GPUJob).filter(GPUJob.user_id == current_user.id)
        
        if status:
            query = query.filter(GPUJob.status == status)
        
        jobs = query.offset(skip).limit(limit).all()
        return jobs
    except Exception as e:
        logger.error(f"Failed to list GPU jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list GPU jobs: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=GPUJobResponse)
async def get_gpu_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get GPU job by ID"""
    try:
        gpu_service = GPUWorkerService(db)
        job = gpu_service.get_gpu_job(job_id, current_user.id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GPU job not found"
            )
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get GPU job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get GPU job: {str(e)}"
        )


@router.post("/jobs/{job_id}/status", response_model=GPUJobResponse)
async def update_job_status(
    job_id: int,
    status_update: JobStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update job status (called by worker agents)"""
    try:
        gpu_service = GPUWorkerService(db)
        job = gpu_service.update_job_status(job_id, status_update)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GPU job not found"
            )
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update job status: {str(e)}"
        )


@router.post("/nodes/{node_id}/jobs/")
async def submit_job_to_node(
    node_id: str,
    job_submission: JobSubmission,
    db: Session = Depends(get_db)
):
    """Submit a job to a specific GPU node"""
    try:
        gpu_service = GPUWorkerService(db)
        success = gpu_service.submit_job_to_node(node_id, job_submission)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit job to node"
            )
        return {"message": f"Job submitted to node {node_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit job to node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job to node: {str(e)}"
        )


@router.get("/available-nodes/")
async def get_available_nodes(
    gpu_memory_required: int = 0,
    cpu_cores_required: int = 0,
    db: Session = Depends(get_db)
):
    """Get available GPU nodes that can handle the requirements"""
    try:
        gpu_service = GPUWorkerService(db)
        nodes = gpu_service.get_available_gpu_nodes(gpu_memory_required, cpu_cores_required)
        return {
            "available_nodes": len(nodes),
            "nodes": [
                {
                    "node_id": node.node_id,
                    "node_name": node.node_name,
                    "gpu_count": node.gpu_count,
                    "gpu_memory_available": node.gpu_memory_available,
                    "cpu_cores_available": node.cpu_cores_available,
                    "current_jobs": node.current_jobs,
                    "max_concurrent_jobs": node.max_concurrent_jobs,
                    "price_per_gpu_hour": node.price_per_gpu_hour
                }
                for node in nodes
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get available nodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available nodes: {str(e)}"
        )


@router.delete("/nodes/{node_id}")
async def delete_gpu_node(
    node_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a GPU node (admin only)"""
    try:
        # Check if user is admin (you might want to add admin role check)
        gpu_service = GPUWorkerService(db)
        node = gpu_service.get_gpu_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GPU node not found"
            )
        
        # Check if node has running jobs
        running_jobs = gpu_service.db.query(GPUJob).filter(
            GPUJob.assigned_node_id == node.id,
            GPUJob.status.in_(["pending", "scheduled", "running"])
        ).count()
        
        if running_jobs > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete node with {running_jobs} running jobs"
            )
        
        # Delete node
        gpu_service.db.delete(node)
        gpu_service.db.commit()
        
        return {"message": f"GPU node {node_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete GPU node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete GPU node: {str(e)}"
        )
