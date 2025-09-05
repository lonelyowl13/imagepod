#!/usr/bin/env python3
"""
ImagePod GPU Worker Agent

This agent runs on GPU nodes and:
1. Registers itself with the main API
2. Monitors GPU resources
3. Receives and executes jobs
4. Reports status back to the API
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import docker
import httpx
import psutil
import GPUtil
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel
import socket
import platform


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_ENDPOINT = os.getenv("API_ENDPOINT", "http://localhost:8000")
REGISTRATION_TOKEN = os.getenv("REGISTRATION_TOKEN", "")
NODE_NAME = os.getenv("NODE_NAME", socket.gethostname())
POD_NAME = os.getenv("POD_NAME", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))

# Global state
worker_state = {
    "node_id": None,
    "agent_id": None,
    "registered": False,
    "running_jobs": {},
    "gpu_info": [],
    "system_info": {},
    "last_heartbeat": None
}

# FastAPI app
app = FastAPI(title="ImagePod GPU Worker Agent", version="1.0.0")

# Docker client
docker_client = None
try:
    docker_client = docker.from_env()
except Exception as e:
    logger.error(f"Failed to initialize Docker client: {e}")


class JobSubmission(BaseModel):
    job_id: int
    docker_image: str
    docker_tag: str = "latest"
    docker_registry: Optional[str] = None
    docker_username: Optional[str] = None
    docker_password: Optional[str] = None
    job_config: Optional[Dict[str, Any]] = None
    input_data: Optional[Dict[str, Any]] = None
    resource_requirements: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = 3600


class JobStatusUpdate(BaseModel):
    job_id: int
    status: str
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    resource_usage: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[float] = None


class NodeHeartbeat(BaseModel):
    node_id: str
    gpu_memory_available: Optional[int] = None
    cpu_cores_available: Optional[int] = None
    memory_available: Optional[int] = None
    storage_available: Optional[int] = None
    current_jobs: Optional[int] = None
    gpu_instances: Optional[List[Dict[str, Any]]] = None
    health_status: Optional[str] = None


def get_gpu_info() -> List[Dict[str, Any]]:
    """Get GPU information using GPUtil"""
    try:
        gpus = GPUtil.getGPUs()
        gpu_info = []
        
        for i, gpu in enumerate(gpus):
            gpu_data = {
                "gpu_index": i,
                "gpu_uuid": gpu.uuid,
                "gpu_name": gpu.name,
                "gpu_type": gpu.name,
                "gpu_memory": gpu.memoryTotal,
                "gpu_memory_available": gpu.memoryFree,
                "utilization": gpu.load * 100,
                "temperature": gpu.temperature,
                "power_usage": None,  # GPUtil doesn't provide power usage
                "status": "available" if gpu.memoryFree > 0 else "busy"
            }
            gpu_info.append(gpu_data)
        
        return gpu_info
    except Exception as e:
        logger.error(f"Failed to get GPU info: {e}")
        return []


def get_system_info() -> Dict[str, Any]:
    """Get system resource information"""
    try:
        # CPU info
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory info
        memory = psutil.virtual_memory()
        memory_total = memory.total // (1024 * 1024)  # Convert to MB
        memory_available = memory.available // (1024 * 1024)  # Convert to MB
        
        # Disk info
        disk = psutil.disk_usage('/')
        disk_total = disk.total // (1024 * 1024 * 1024)  # Convert to GB
        disk_available = disk.free // (1024 * 1024 * 1024)  # Convert to GB
        
        return {
            "cpu_cores": cpu_count,
            "cpu_utilization": cpu_percent,
            "memory_total": memory_total,
            "memory_available": memory_available,
            "disk_total": disk_total,
            "disk_available": disk_available,
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": platform.python_version()
        }
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return {}


async def register_with_api():
    """Register this worker with the main API"""
    try:
        gpu_info = get_gpu_info()
        system_info = get_system_info()
        
        # Generate unique agent ID
        agent_id = f"agent-{NODE_NAME}-{int(time.time())}"
        
        # Prepare registration data
        registration_data = {
            "node_name": NODE_NAME,
            "hostname": socket.gethostname(),
            "ip_address": socket.gethostbyname(socket.gethostname()),
            "cluster_name": "default",
            "gpu_count": len(gpu_info),
            "gpu_type": gpu_info[0]["gpu_name"] if gpu_info else None,
            "gpu_memory_total": sum(gpu["gpu_memory"] for gpu in gpu_info),
            "cpu_cores": system_info.get("cpu_cores", 0),
            "memory_total": system_info.get("memory_total", 0),
            "storage_total": system_info.get("disk_total", 0),
            "max_concurrent_jobs": MAX_CONCURRENT_JOBS,
            "auto_register": True,
            "k8s_node_name": NODE_NAME,
            "k8s_cluster": "default",
            "k8s_namespace": "imagepod",
            "api_endpoint": f"http://{socket.gethostbyname(socket.gethostname())}:8080",
            "node_metadata": {
                "pod_name": POD_NAME,
                "platform": system_info.get("platform"),
                "python_version": system_info.get("python_version")
            }
        }
        
        # Register node
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_ENDPOINT}/gpu-workers/nodes/register",
                json=registration_data,
                headers={"Authorization": f"Bearer {REGISTRATION_TOKEN}"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                node_data = response.json()
                worker_state["node_id"] = node_data["node_id"]
                worker_state["registered"] = True
                logger.info(f"Successfully registered node: {node_data['node_id']}")
                
                # Register agent
                agent_data = {
                    "node_id": node_data["id"],
                    "agent_id": agent_id,
                    "agent_version": "1.0.0",
                    "config": {
                        "heartbeat_interval": HEARTBEAT_INTERVAL,
                        "max_concurrent_jobs": MAX_CONCURRENT_JOBS
                    },
                    "capabilities": {
                        "docker": docker_client is not None,
                        "gpu_count": len(gpu_info),
                        "gpu_types": [gpu["gpu_name"] for gpu in gpu_info]
                    },
                    "api_endpoint": f"http://{socket.gethostbyname(socket.gethostname())}:8080",
                    "websocket_endpoint": f"ws://{socket.gethostbyname(socket.gethostname())}:8081"
                }
                
                agent_response = await client.post(
                    f"{API_ENDPOINT}/gpu-workers/agents/register",
                    json=agent_data,
                    headers={"Authorization": f"Bearer {REGISTRATION_TOKEN}"},
                    timeout=30.0
                )
                
                if agent_response.status_code == 200:
                    agent_data = agent_response.json()
                    worker_state["agent_id"] = agent_data["id"]
                    logger.info(f"Successfully registered agent: {agent_id}")
                else:
                    logger.error(f"Failed to register agent: {agent_response.text}")
            else:
                logger.error(f"Failed to register node: {response.text}")
                
    except Exception as e:
        logger.error(f"Failed to register with API: {e}")


async def send_heartbeat():
    """Send heartbeat to the main API"""
    if not worker_state["registered"] or not worker_state["node_id"]:
        return
    
    try:
        gpu_info = get_gpu_info()
        system_info = get_system_info()
        
        # Calculate available resources
        gpu_memory_available = sum(gpu["gpu_memory_available"] for gpu in gpu_info)
        cpu_cores_available = system_info.get("cpu_cores", 0) - len(worker_state["running_jobs"])
        memory_available = system_info.get("memory_available", 0)
        storage_available = system_info.get("disk_available", 0)
        
        heartbeat_data = {
            "node_id": worker_state["node_id"],
            "gpu_memory_available": gpu_memory_available,
            "cpu_cores_available": cpu_cores_available,
            "memory_available": memory_available,
            "storage_available": storage_available,
            "current_jobs": len(worker_state["running_jobs"]),
            "gpu_instances": gpu_info,
            "health_status": "healthy"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_ENDPOINT}/gpu-workers/nodes/{worker_state['node_id']}/heartbeat",
                json=heartbeat_data,
                headers={"Authorization": f"Bearer {REGISTRATION_TOKEN}"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                worker_state["last_heartbeat"] = datetime.utcnow()
                logger.debug("Heartbeat sent successfully")
            else:
                logger.error(f"Failed to send heartbeat: {response.text}")
                
    except Exception as e:
        logger.error(f"Failed to send heartbeat: {e}")


async def execute_job(job_submission: JobSubmission):
    """Execute a job using Docker"""
    job_id = job_submission.job_id
    logger.info(f"Starting job {job_id}")
    
    try:
        # Update job status to running
        await update_job_status(job_id, "running")
        
        # Pull Docker image if needed
        image_name = f"{job_submission.docker_image}:{job_submission.docker_tag}"
        if job_submission.docker_registry:
            image_name = f"{job_submission.docker_registry}/{image_name}"
        
        logger.info(f"Pulling image: {image_name}")
        if docker_client:
            docker_client.images.pull(image_name)
        
        # Prepare job data
        job_data = {
            "job_id": job_id,
            "input_data": job_submission.input_data,
            "config": job_submission.job_config,
            "resource_requirements": job_submission.resource_requirements
        }
        
        # Run Docker container
        container_name = f"imagepod-job-{job_id}"
        container_config = {
            "image": image_name,
            "name": container_name,
            "environment": {
                "JOB_DATA": json.dumps(job_data),
                "API_ENDPOINT": API_ENDPOINT,
                "JOB_ID": str(job_id)
            },
            "volumes": {
                "/tmp/imagepod": {"bind": "/data", "mode": "rw"}
            },
            "detach": True,
            "remove": True
        }
        
        # Add GPU support if available
        if docker_client and hasattr(docker_client, 'api'):
            container_config["runtime"] = "nvidia"
        
        logger.info(f"Starting container: {container_name}")
        if docker_client:
            container = docker_client.containers.run(**container_config)
            worker_state["running_jobs"][job_id] = {
                "container": container,
                "start_time": datetime.utcnow(),
                "submission": job_submission
            }
        
        # Monitor job execution
        await monitor_job(job_id)
        
    except Exception as e:
        logger.error(f"Failed to execute job {job_id}: {e}")
        await update_job_status(job_id, "failed", error_message=str(e))


async def monitor_job(job_id: int):
    """Monitor a running job"""
    if job_id not in worker_state["running_jobs"]:
        return
    
    job_info = worker_state["running_jobs"][job_id]
    container = job_info["container"]
    start_time = job_info["start_time"]
    
    try:
        # Wait for container to complete
        if docker_client:
            result = container.wait(timeout=3600)  # 1 hour timeout
            
            # Get container logs
            logs = container.logs().decode('utf-8')
            
            # Get resource usage
            stats = container.stats(stream=False)
            resource_usage = {
                "cpu_usage": stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0),
                "memory_usage": stats.get("memory_stats", {}).get("usage", 0),
                "gpu_memory": None  # Would need nvidia-docker stats
            }
            
            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            if result["StatusCode"] == 0:
                # Job completed successfully
                output_data = {"logs": logs, "exit_code": 0}
                await update_job_status(job_id, "completed", output_data, resource_usage, duration)
            else:
                # Job failed
                error_message = f"Container exited with code {result['StatusCode']}: {logs}"
                await update_job_status(job_id, "failed", error_message=error_message, resource_usage=resource_usage, duration=duration)
    
    except Exception as e:
        logger.error(f"Failed to monitor job {job_id}: {e}")
        await update_job_status(job_id, "failed", error_message=str(e))
    
    finally:
        # Clean up
        if job_id in worker_state["running_jobs"]:
            del worker_state["running_jobs"][job_id]


async def update_job_status(job_id: int, status: str, output_data: Optional[Dict[str, Any]] = None, 
                          resource_usage: Optional[Dict[str, Any]] = None, duration: Optional[float] = None,
                          error_message: Optional[str] = None):
    """Update job status in the main API"""
    try:
        status_update = {
            "job_id": job_id,
            "status": status,
            "output_data": output_data,
            "error_message": error_message,
            "resource_usage": resource_usage,
            "duration_seconds": duration
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_ENDPOINT}/gpu-workers/jobs/{job_id}/status",
                json=status_update,
                headers={"Authorization": f"Bearer {REGISTRATION_TOKEN}"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                logger.info(f"Updated job {job_id} status to {status}")
            else:
                logger.error(f"Failed to update job status: {response.text}")
                
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")


# FastAPI endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    return {"status": "ready", "registered": worker_state["registered"]}


@app.get("/status")
async def get_status():
    """Get worker status"""
    return {
        "node_id": worker_state["node_id"],
        "agent_id": worker_state["agent_id"],
        "registered": worker_state["registered"],
        "running_jobs": len(worker_state["running_jobs"]),
        "gpu_info": get_gpu_info(),
        "system_info": get_system_info(),
        "last_heartbeat": worker_state["last_heartbeat"]
    }


@app.post("/jobs/")
async def submit_job(job_submission: JobSubmission, background_tasks: BackgroundTasks):
    """Submit a new job for execution"""
    if len(worker_state["running_jobs"]) >= MAX_CONCURRENT_JOBS:
        raise HTTPException(status_code=429, detail="Maximum concurrent jobs reached")
    
    if not worker_state["registered"]:
        raise HTTPException(status_code=503, detail="Worker not registered")
    
    # Start job execution in background
    background_tasks.add_task(execute_job, job_submission)
    
    return {"message": f"Job {job_submission.job_id} submitted for execution"}


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: int):
    """Get job status"""
    if job_id in worker_state["running_jobs"]:
        job_info = worker_state["running_jobs"][job_id]
        return {
            "job_id": job_id,
            "status": "running",
            "start_time": job_info["start_time"].isoformat(),
            "duration": (datetime.utcnow() - job_info["start_time"]).total_seconds()
        }
    else:
        return {"job_id": job_id, "status": "not_found"}


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: int):
    """Cancel a running job"""
    if job_id not in worker_state["running_jobs"]:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = worker_state["running_jobs"][job_id]
    container = job_info["container"]
    
    try:
        if docker_client:
            container.stop()
            container.remove()
        
        await update_job_status(job_id, "cancelled")
        del worker_state["running_jobs"][job_id]
        
        return {"message": f"Job {job_id} cancelled"}
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def heartbeat_loop():
    """Background task to send heartbeats"""
    while True:
        try:
            await send_heartbeat()
            await asyncio.sleep(HEARTBEAT_INTERVAL)
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")
            await asyncio.sleep(HEARTBEAT_INTERVAL)


async def startup_event():
    """Startup event handler"""
    logger.info("Starting ImagePod GPU Worker Agent")
    
    # Register with API
    await register_with_api()
    
    # Start heartbeat loop
    asyncio.create_task(heartbeat_loop())


def signal_handler(signum, frame):
    """Signal handler for graceful shutdown"""
    logger.info("Received shutdown signal, cleaning up...")
    
    # Stop all running jobs
    for job_id, job_info in worker_state["running_jobs"].items():
        try:
            container = job_info["container"]
            if docker_client:
                container.stop()
                container.remove()
        except Exception as e:
            logger.error(f"Failed to stop job {job_id}: {e}")
    
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Add startup event
    app.add_event_handler("startup", startup_event)
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level=LOG_LEVEL.lower()
    )
