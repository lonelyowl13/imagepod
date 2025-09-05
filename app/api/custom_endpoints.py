from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database import get_db
from app.services.endpoint_service import EndpointService
from app.schemas.endpoint import EndpointJobRequest, EndpointJobResponse
import json


# Create a dynamic router for custom endpoints
custom_endpoint_router = APIRouter()


@custom_endpoint_router.post("/endpoint/{endpoint_id}/jobs/", response_model=EndpointJobResponse)
async def custom_endpoint_jobs(
    endpoint_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle job requests to custom endpoints"""
    endpoint_service = EndpointService(db)
    
    # Check if endpoint exists
    endpoint = endpoint_service.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    if endpoint.status != "active":
        raise HTTPException(status_code=503, detail="Endpoint is not active")
    
    # Get request body
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    # Create job request
    job_request = EndpointJobRequest(
        input=body,
        timeout=300,  # Default timeout
        priority="normal"
    )
    
    # Create job
    result = endpoint_service.create_endpoint_job(endpoint_id, job_request)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create job")
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@custom_endpoint_router.get("/endpoint/{endpoint_id}/jobs/{job_id}", response_model=EndpointJobResponse)
async def custom_endpoint_job_status(
    endpoint_id: str,
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get job status from custom endpoint"""
    endpoint_service = EndpointService(db)
    
    # Check if endpoint exists
    endpoint = endpoint_service.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Get job status
    result = endpoint_service.get_endpoint_job(endpoint_id, job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return result


@custom_endpoint_router.get("/endpoint/{endpoint_id}/health")
async def custom_endpoint_health(
    endpoint_id: str,
    db: Session = Depends(get_db)
):
    """Health check for custom endpoint"""
    endpoint_service = EndpointService(db)
    
    # Check if endpoint exists
    endpoint = endpoint_service.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return {
        "status": endpoint.status,
        "health_status": endpoint.health_status,
        "current_replicas": endpoint.current_replicas,
        "total_requests": endpoint.total_requests,
        "successful_requests": endpoint.successful_requests,
        "failed_requests": endpoint.failed_requests
    }


@custom_endpoint_router.get("/endpoint/{endpoint_id}/info")
async def custom_endpoint_info(
    endpoint_id: str,
    db: Session = Depends(get_db)
):
    """Get endpoint information"""
    endpoint_service = EndpointService(db)
    
    # Check if endpoint exists
    endpoint = endpoint_service.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return {
        "endpoint_id": endpoint.endpoint_id,
        "name": endpoint.name,
        "description": endpoint.description,
        "status": endpoint.status,
        "health_status": endpoint.health_status,
        "is_public": endpoint.is_public,
        "api_key_required": endpoint.api_key_required,
        "rate_limit": endpoint.rate_limit,
        "current_replicas": endpoint.current_replicas,
        "created_at": endpoint.created_at.isoformat() if endpoint.created_at else None,
        "deployed_at": endpoint.deployed_at.isoformat() if endpoint.deployed_at else None
    }


# Generic catch-all route for custom endpoint paths
@custom_endpoint_router.api_route("/endpoint/{endpoint_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def custom_endpoint_catch_all(
    endpoint_id: str,
    path: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Catch-all route for custom endpoint paths"""
    endpoint_service = EndpointService(db)
    
    # Check if endpoint exists
    endpoint = endpoint_service.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    if endpoint.status != "active":
        raise HTTPException(status_code=503, detail="Endpoint is not active")
    
    # Get request details
    method = request.method
    headers = dict(request.headers)
    
    # Get request body for non-GET requests
    body = {}
    if method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except Exception:
            try:
                body = await request.form()
            except Exception:
                pass
    
    # Get query parameters
    query_params = dict(request.query_params)
    
    # Create a job request with the full request context
    job_request = EndpointJobRequest(
        input={
            "method": method,
            "path": path,
            "headers": headers,
            "body": body,
            "query_params": query_params,
            "endpoint_id": endpoint_id
        },
        timeout=300,
        priority="normal"
    )
    
    # Create job
    result = endpoint_service.create_endpoint_job(endpoint_id, job_request)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to process request")
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# Alternative routing for direct endpoint access
@custom_endpoint_router.api_route("/{endpoint_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def direct_endpoint_access(
    endpoint_id: str,
    path: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Direct endpoint access without /endpoint/ prefix"""
    endpoint_service = EndpointService(db)
    
    # Check if endpoint exists
    endpoint = endpoint_service.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    if endpoint.status != "active":
        raise HTTPException(status_code=503, detail="Endpoint is not active")
    
    # Get request details
    method = request.method
    headers = dict(request.headers)
    
    # Get request body for non-GET requests
    body = {}
    if method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except Exception:
            try:
                body = await request.form()
            except Exception:
                pass
    
    # Get query parameters
    query_params = dict(request.query_params)
    
    # Create a job request with the full request context
    job_request = EndpointJobRequest(
        input={
            "method": method,
            "path": path,
            "headers": headers,
            "body": body,
            "query_params": query_params,
            "endpoint_id": endpoint_id
        },
        timeout=300,
        priority="normal"
    )
    
    # Create job
    result = endpoint_service.create_endpoint_job(endpoint_id, job_request)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to process request")
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result
