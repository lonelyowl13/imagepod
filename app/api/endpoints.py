from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.auth import get_current_active_user, get_current_superuser
from app.models.user import User
from app.schemas.endpoint import (
    EndpointCreate, EndpointUpdate, EndpointResponse, EndpointDeploymentResponse,
    EndpointJobRequest, EndpointJobResponse, EndpointStatsResponse, 
    DockerImageUpload, EndpointScaleRequest
)
from app.services.endpoint_service import EndpointService

router = APIRouter(prefix="/endpoints", tags=["endpoints"])


@router.post("/", response_model=EndpointResponse)
async def create_endpoint(
    endpoint_data: EndpointCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new endpoint"""
    endpoint_service = EndpointService(db)
    
    try:
        endpoint = endpoint_service.create_endpoint(current_user.id, endpoint_data)
        return endpoint
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[EndpointResponse])
async def get_user_endpoints(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's endpoints"""
    endpoint_service = EndpointService(db)
    endpoints = endpoint_service.get_user_endpoints(current_user.id, skip, limit)
    return endpoints


@router.get("/public/", response_model=List[EndpointResponse])
async def get_public_endpoints(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get public endpoints"""
    endpoint_service = EndpointService(db)
    endpoints = endpoint_service.get_public_endpoints(skip, limit)
    return endpoints


@router.get("/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint(
    endpoint_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific endpoint"""
    endpoint_service = EndpointService(db)
    endpoint = endpoint_service.get_endpoint(endpoint_id, current_user.id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return endpoint


@router.put("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: str,
    endpoint_update: EndpointUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an endpoint"""
    endpoint_service = EndpointService(db)
    endpoint = endpoint_service.get_endpoint(endpoint_id, current_user.id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    updated_endpoint = endpoint_service.update_endpoint(endpoint.id, endpoint_update, current_user.id)
    if not updated_endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return updated_endpoint


@router.delete("/{endpoint_id}")
async def delete_endpoint(
    endpoint_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an endpoint"""
    endpoint_service = EndpointService(db)
    endpoint = endpoint_service.get_endpoint(endpoint_id, current_user.id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    success = endpoint_service.delete_endpoint(endpoint.id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return {"message": "Endpoint deleted successfully"}


@router.post("/{endpoint_id}/scale")
async def scale_endpoint(
    endpoint_id: str,
    scale_request: EndpointScaleRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Scale an endpoint"""
    endpoint_service = EndpointService(db)
    endpoint = endpoint_service.get_endpoint(endpoint_id, current_user.id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    success = endpoint_service.scale_endpoint(endpoint.id, scale_request.target_replicas, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to scale endpoint")
    
    return {"message": f"Endpoint scaled to {scale_request.target_replicas} replicas"}


@router.get("/{endpoint_id}/stats", response_model=EndpointStatsResponse)
async def get_endpoint_stats(
    endpoint_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get endpoint statistics"""
    endpoint_service = EndpointService(db)
    endpoint = endpoint_service.get_endpoint(endpoint_id, current_user.id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    stats = endpoint_service.get_endpoint_stats(endpoint.id, current_user.id)
    if not stats:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return stats


@router.get("/{endpoint_id}/deployments/", response_model=List[EndpointDeploymentResponse])
async def get_endpoint_deployments(
    endpoint_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get endpoint deployments"""
    endpoint_service = EndpointService(db)
    endpoint = endpoint_service.get_endpoint(endpoint_id, current_user.id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Get deployments from database
    from app.models.endpoint import EndpointDeployment
    deployments = (
        db.query(EndpointDeployment)
        .filter(EndpointDeployment.endpoint_id == endpoint.id)
        .order_by(EndpointDeployment.created_at.desc())
        .all()
    )
    
    return deployments


@router.post("/upload-image")
async def upload_docker_image(
    image_upload: DockerImageUpload,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload Docker image to registry"""
    # This would integrate with Docker registry APIs
    # For now, just return success
    return {
        "message": "Image upload initiated",
        "image_name": image_upload.image_name,
        "image_tag": image_upload.image_tag,
        "registry_url": image_upload.registry_url
    }


@router.post("/upload-image-file")
async def upload_docker_image_file(
    file: UploadFile = File(...),
    image_name: str = Query(...),
    image_tag: str = Query("latest"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload Docker image file"""
    # This would handle Docker image file uploads
    # For now, just return success
    return {
        "message": "Image file upload initiated",
        "filename": file.filename,
        "image_name": image_name,
        "image_tag": image_tag,
        "size": file.size
    }


# Custom endpoint routing for job execution
@router.post("/{endpoint_id}/jobs/", response_model=EndpointJobResponse)
async def create_endpoint_job(
    endpoint_id: str,
    job_request: EndpointJobRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a job for an endpoint"""
    endpoint_service = EndpointService(db)
    
    # Check if endpoint exists and user has access
    endpoint = endpoint_service.get_endpoint(endpoint_id, current_user.id)
    if not endpoint:
        # Check if it's a public endpoint
        endpoint = endpoint_service.get_endpoint(endpoint_id)
        if not endpoint or not endpoint.is_public:
            raise HTTPException(status_code=404, detail="Endpoint not found")
    
    result = endpoint_service.create_endpoint_job(endpoint_id, job_request, current_user.id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create job")
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/{endpoint_id}/jobs/{job_id}", response_model=EndpointJobResponse)
async def get_endpoint_job(
    endpoint_id: str,
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get job status from endpoint"""
    endpoint_service = EndpointService(db)
    
    # Check if endpoint exists and user has access
    endpoint = endpoint_service.get_endpoint(endpoint_id, current_user.id)
    if not endpoint:
        # Check if it's a public endpoint
        endpoint = endpoint_service.get_endpoint(endpoint_id)
        if not endpoint or not endpoint.is_public:
            raise HTTPException(status_code=404, detail="Endpoint not found")
    
    result = endpoint_service.get_endpoint_job(endpoint_id, job_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return result


# Public endpoint access (no authentication required for public endpoints)
@router.post("/public/{endpoint_id}/jobs/", response_model=EndpointJobResponse)
async def create_public_endpoint_job(
    endpoint_id: str,
    job_request: EndpointJobRequest,
    db: Session = Depends(get_db)
):
    """Create a job for a public endpoint (no authentication required)"""
    endpoint_service = EndpointService(db)
    
    # Check if endpoint exists and is public
    endpoint = endpoint_service.get_endpoint(endpoint_id)
    if not endpoint or not endpoint.is_public:
        raise HTTPException(status_code=404, detail="Public endpoint not found")
    
    result = endpoint_service.create_endpoint_job(endpoint_id, job_request)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create job")
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/public/{endpoint_id}/jobs/{job_id}", response_model=EndpointJobResponse)
async def get_public_endpoint_job(
    endpoint_id: str,
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get job status from public endpoint (no authentication required)"""
    endpoint_service = EndpointService(db)
    
    # Check if endpoint exists and is public
    endpoint = endpoint_service.get_endpoint(endpoint_id)
    if not endpoint or not endpoint.is_public:
        raise HTTPException(status_code=404, detail="Public endpoint not found")
    
    result = endpoint_service.get_endpoint_job(endpoint_id, job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return result
