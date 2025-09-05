from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from app.models.gpu_worker import GPUNode, GPUInstance, GPUJob, WorkerAgent
from app.schemas.gpu_worker import (
    GPUNodeRegistration, GPUNodeUpdate, GPUJobCreate, GPUJobUpdate,
    WorkerAgentRegistration, WorkerAgentUpdate, NodeHeartbeat, JobSubmission,
    JobStatusUpdate, NodeStats
)
import uuid
import docker
import kubernetes
from kubernetes import client, config
from app.config import settings
from datetime import datetime, timedelta
import asyncio
import httpx
import json
import base64
from cryptography.fernet import Fernet


class GPUWorkerService:
    def __init__(self, db: Session):
        self.db = db
        self.docker_client = None
        self.k8s_client = None
        self.encryption_key = settings.secret_key.encode()[:32].ljust(32, b'0')
        self.cipher = Fernet(base64.urlsafe_b64encode(self.encryption_key))
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            print(f"Failed to initialize Docker client: {e}")
        
        # Initialize Kubernetes client
        try:
            if settings.kubeconfig_path:
                config.load_kube_config(config_file=settings.kubeconfig_path)
            else:
                config.load_incluster_config()
            self.k8s_client = client.ApiClient()
        except Exception as e:
            print(f"Failed to initialize Kubernetes client: {e}")

    def register_gpu_node(self, node_data: GPUNodeRegistration) -> GPUNode:
        """Register a new GPU node"""
        # Generate node ID if not provided
        node_id = node_data.node_id or self._generate_node_id()
        
        # Check if node already exists
        existing_node = self.db.query(GPUNode).filter(
            GPUNode.node_name == node_data.node_name
        ).first()
        
        if existing_node:
            # Update existing node
            return self._update_node_from_registration(existing_node, node_data)
        
        # Create new node
        db_node = GPUNode(
            node_name=node_data.node_name,
            node_id=node_id,
            hostname=node_data.hostname,
            ip_address=node_data.ip_address,
            region=node_data.region,
            zone=node_data.zone,
            cluster_name=node_data.cluster_name,
            gpu_count=node_data.gpu_count,
            gpu_type=node_data.gpu_type,
            gpu_memory_total=node_data.gpu_memory_total,
            gpu_driver_version=node_data.gpu_driver_version,
            gpu_cuda_version=node_data.gpu_cuda_version,
            cpu_cores=node_data.cpu_cores,
            memory_total=node_data.memory_total,
            storage_total=node_data.storage_total,
            max_concurrent_jobs=node_data.max_concurrent_jobs,
            auto_register=node_data.auto_register,
            price_per_gpu_hour=node_data.price_per_gpu_hour,
            price_per_cpu_hour=node_data.price_per_cpu_hour,
            price_per_memory_gb_hour=node_data.price_per_memory_gb_hour,
            k8s_node_name=node_data.k8s_node_name,
            k8s_cluster=node_data.k8s_cluster,
            k8s_namespace=node_data.k8s_namespace,
            k8s_labels=node_data.k8s_labels,
            k8s_taints=node_data.k8s_taints,
            api_endpoint=node_data.api_endpoint,
            ssh_endpoint=node_data.ssh_endpoint,
            vnc_endpoint=node_data.vnc_endpoint,
            node_metadata=node_data.node_metadata,
            status="active",
            health_status="healthy",
            registered_at=datetime.utcnow(),
            last_seen=datetime.utcnow()
        )

        self.db.add(db_node)
        self.db.commit()
        self.db.refresh(db_node)

        # Create GPU instances
        self._create_gpu_instances(db_node)

        return db_node

    def get_gpu_node(self, node_id: str) -> Optional[GPUNode]:
        """Get GPU node by node_id"""
        return self.db.query(GPUNode).filter(GPUNode.node_id == node_id).first()

    def get_gpu_node_by_name(self, node_name: str) -> Optional[GPUNode]:
        """Get GPU node by node name"""
        return self.db.query(GPUNode).filter(GPUNode.node_name == node_name).first()

    def get_available_gpu_nodes(self, gpu_memory_required: int = 0, cpu_cores_required: int = 0) -> List[GPUNode]:
        """Get available GPU nodes that can handle the requirements"""
        query = self.db.query(GPUNode).filter(
            GPUNode.status == "active",
            GPUNode.health_status == "healthy",
            GPUNode.current_jobs < GPUNode.max_concurrent_jobs
        )

        if gpu_memory_required > 0:
            query = query.filter(GPUNode.gpu_memory_available >= gpu_memory_required)
        
        if cpu_cores_required > 0:
            query = query.filter(GPUNode.cpu_cores_available >= cpu_cores_required)

        return query.all()

    def update_node_heartbeat(self, node_id: str, heartbeat_data: NodeHeartbeat) -> Optional[GPUNode]:
        """Update node heartbeat and status"""
        node = self.get_gpu_node(node_id)
        if not node:
            return None

        # Update node status
        if heartbeat_data.gpu_memory_available is not None:
            node.gpu_memory_available = heartbeat_data.gpu_memory_available
        if heartbeat_data.cpu_cores_available is not None:
            node.cpu_cores_available = heartbeat_data.cpu_cores_available
        if heartbeat_data.memory_available is not None:
            node.memory_available = heartbeat_data.memory_available
        if heartbeat_data.current_jobs is not None:
            node.current_jobs = heartbeat_data.current_jobs
        if heartbeat_data.health_status is not None:
            node.health_status = heartbeat_data.health_status

        node.last_heartbeat = datetime.utcnow()
        node.last_seen = datetime.utcnow()

        # Update GPU instances if provided
        if heartbeat_data.gpu_instances:
            self._update_gpu_instances(node, heartbeat_data.gpu_instances)

        self.db.commit()
        self.db.refresh(node)
        return node

    def create_gpu_job(self, user_id: int, job_data: GPUJobCreate) -> GPUJob:
        """Create a new GPU job"""
        db_job = GPUJob(
            user_id=user_id,
            endpoint_id=job_data.endpoint_id,
            job_name=job_data.job_name,
            job_type=job_data.job_type,
            docker_image=job_data.docker_image,
            docker_tag=job_data.docker_tag,
            docker_registry=job_data.docker_registry,
            job_config=job_data.job_config,
            input_data=job_data.input_data,
            gpu_memory_required=job_data.gpu_memory_required,
            cpu_cores_required=job_data.cpu_cores_required,
            memory_required=job_data.memory_required,
            storage_required=job_data.storage_required,
            status="pending"
        )

        self.db.add(db_job)
        self.db.commit()
        self.db.refresh(db_job)

        # Try to schedule the job
        self._schedule_job(db_job)

        return db_job

    def get_gpu_job(self, job_id: int, user_id: Optional[int] = None) -> Optional[GPUJob]:
        """Get GPU job by ID"""
        query = self.db.query(GPUJob).filter(GPUJob.id == job_id)
        if user_id:
            query = query.filter(GPUJob.user_id == user_id)
        return query.first()

    def update_job_status(self, job_id: int, status_update: JobStatusUpdate) -> Optional[GPUJob]:
        """Update job status from GPU node"""
        job = self.get_gpu_job(job_id)
        if not job:
            return None

        # Update job status
        job.status = status_update.status
        
        if status_update.status == "running" and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status_update.status in ["completed", "failed", "cancelled"] and not job.completed_at:
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.duration_seconds = (job.completed_at - job.started_at).total_seconds()

        if status_update.output_data is not None:
            job.output_data = status_update.output_data

        if status_update.error_message is not None:
            job.error_message = status_update.error_message

        if status_update.resource_usage:
            job.gpu_memory_used = status_update.resource_usage.get("gpu_memory")
            job.cpu_cores_used = status_update.resource_usage.get("cpu_cores")
            job.memory_used = status_update.resource_usage.get("memory")
            job.storage_used = status_update.resource_usage.get("storage")

        if status_update.duration_seconds is not None:
            job.duration_seconds = status_update.duration_seconds

        # Calculate cost
        if job.status == "completed" and job.duration_seconds and job.assigned_node:
            job.cost = self._calculate_job_cost(job)

        # Update node job count
        if job.assigned_node:
            if status_update.status == "running" and job.status != "running":
                job.assigned_node.current_jobs += 1
            elif status_update.status in ["completed", "failed", "cancelled"] and job.status == "running":
                job.assigned_node.current_jobs = max(0, job.assigned_node.current_jobs - 1)

        self.db.commit()
        self.db.refresh(job)
        return job

    def submit_job_to_node(self, node_id: str, job_submission: JobSubmission) -> bool:
        """Submit a job to a specific GPU node"""
        node = self.get_gpu_node(node_id)
        if not node or not node.api_endpoint:
            return False

        try:
            # Send job to node via HTTP
            async def submit_job():
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{node.api_endpoint}/jobs/",
                        json=job_submission.dict(),
                        timeout=30.0
                    )
                    return response.status_code == 200

            # Run async function
            import asyncio
            return asyncio.run(submit_job())

        except Exception as e:
            print(f"Failed to submit job to node {node_id}: {e}")
            return False

    def get_node_stats(self, node_id: str) -> Optional[NodeStats]:
        """Get node statistics"""
        node = self.get_gpu_node(node_id)
        if not node:
            return None

        # Get GPU instances
        gpu_instances = self.db.query(GPUInstance).filter(
            GPUInstance.node_id == node.id
        ).all()

        gpu_utilization = [gpu.utilization for gpu in gpu_instances]
        temperature = [gpu.temperature for gpu in gpu_instances]
        power_usage = [gpu.power_usage for gpu in gpu_instances]

        utilization_percentage = sum(gpu_utilization) / len(gpu_utilization) if gpu_utilization else 0.0

        return NodeStats(
            total_gpu_memory=node.gpu_memory_total or 0,
            available_gpu_memory=node.gpu_memory_available or 0,
            total_cpu_cores=node.cpu_cores or 0,
            available_cpu_cores=node.cpu_cores_available or 0,
            total_memory=node.memory_total or 0,
            available_memory=node.memory_available or 0,
            current_jobs=node.current_jobs,
            max_concurrent_jobs=node.max_concurrent_jobs,
            utilization_percentage=utilization_percentage,
            gpu_utilization=gpu_utilization,
            temperature=temperature,
            power_usage=power_usage
        )

    def register_worker_agent(self, agent_data: WorkerAgentRegistration) -> WorkerAgent:
        """Register a worker agent"""
        # Check if agent already exists
        existing_agent = self.db.query(WorkerAgent).filter(
            WorkerAgent.agent_id == agent_data.agent_id
        ).first()

        if existing_agent:
            # Update existing agent
            existing_agent.status = "active"
            existing_agent.health_status = "healthy"
            existing_agent.last_heartbeat = datetime.utcnow()
            existing_agent.config = agent_data.config
            existing_agent.capabilities = agent_data.capabilities
            existing_agent.api_endpoint = agent_data.api_endpoint
            existing_agent.websocket_endpoint = agent_data.websocket_endpoint
            self.db.commit()
            return existing_agent

        # Create new agent
        db_agent = WorkerAgent(
            node_id=agent_data.node_id,
            agent_id=agent_data.agent_id,
            agent_version=agent_data.agent_version,
            config=agent_data.config,
            capabilities=agent_data.capabilities,
            api_endpoint=agent_data.api_endpoint,
            websocket_endpoint=agent_data.websocket_endpoint,
            status="active",
            health_status="healthy",
            last_heartbeat=datetime.utcnow(),
            started_at=datetime.utcnow()
        )

        self.db.add(db_agent)
        self.db.commit()
        self.db.refresh(db_agent)
        return db_agent

    def _generate_node_id(self) -> str:
        """Generate a unique node ID"""
        return f"gpu-{uuid.uuid4().hex[:12]}"

    def _update_node_from_registration(self, node: GPUNode, node_data: GPUNodeRegistration) -> GPUNode:
        """Update existing node from registration data"""
        node.hostname = node_data.hostname
        node.ip_address = node_data.ip_address
        node.region = node_data.region
        node.zone = node_data.zone
        node.gpu_count = node_data.gpu_count
        node.gpu_type = node_data.gpu_type
        node.gpu_memory_total = node_data.gpu_memory_total
        node.gpu_driver_version = node_data.gpu_driver_version
        node.gpu_cuda_version = node_data.gpu_cuda_version
        node.cpu_cores = node_data.cpu_cores
        node.memory_total = node_data.memory_total
        node.storage_total = node_data.storage_total
        node.max_concurrent_jobs = node_data.max_concurrent_jobs
        node.price_per_gpu_hour = node_data.price_per_gpu_hour
        node.price_per_cpu_hour = node_data.price_per_cpu_hour
        node.price_per_memory_gb_hour = node_data.price_per_memory_gb_hour
        node.k8s_node_name = node_data.k8s_node_name
        node.k8s_cluster = node_data.k8s_cluster
        node.k8s_namespace = node_data.k8s_namespace
        node.k8s_labels = node_data.k8s_labels
        node.k8s_taints = node_data.k8s_taints
        node.api_endpoint = node_data.api_endpoint
        node.ssh_endpoint = node_data.ssh_endpoint
        node.vnc_endpoint = node_data.vnc_endpoint
        node.node_metadata = node_data.node_metadata
        node.status = "active"
        node.health_status = "healthy"
        node.last_seen = datetime.utcnow()

        self.db.commit()
        self.db.refresh(node)
        return node

    def _create_gpu_instances(self, node: GPUNode):
        """Create GPU instances for a node"""
        for i in range(node.gpu_count):
            gpu_instance = GPUInstance(
                node_id=node.id,
                gpu_index=i,
                gpu_uuid=f"{node.node_id}-gpu-{i}",
                gpu_name=f"{node.gpu_type or 'GPU'}-{i}",
                gpu_type=node.gpu_type,
                gpu_memory=node.gpu_memory_total // node.gpu_count if node.gpu_memory_total else None,
                status="available"
            )
            self.db.add(gpu_instance)

        self.db.commit()

    def _update_gpu_instances(self, node: GPUNode, gpu_instances_data: List[Dict[str, Any]]):
        """Update GPU instances from heartbeat data"""
        for gpu_data in gpu_instances_data:
            gpu_index = gpu_data.get("gpu_index")
            if gpu_index is not None:
                gpu_instance = self.db.query(GPUInstance).filter(
                    GPUInstance.node_id == node.id,
                    GPUInstance.gpu_index == gpu_index
                ).first()

                if gpu_instance:
                    gpu_instance.utilization = gpu_data.get("utilization", 0.0)
                    gpu_instance.temperature = gpu_data.get("temperature")
                    gpu_instance.power_usage = gpu_data.get("power_usage")
                    gpu_instance.status = gpu_data.get("status", "available")
                    gpu_instance.last_heartbeat = datetime.utcnow()

        self.db.commit()

    def _schedule_job(self, job: GPUJob):
        """Schedule a job to an available GPU node"""
        # Find available nodes
        available_nodes = self.get_available_gpu_nodes(
            gpu_memory_required=job.gpu_memory_required or 0,
            cpu_cores_required=job.cpu_cores_required or 0
        )

        if not available_nodes:
            # No available nodes, keep job as pending
            return

        # Select best node (simple selection for now)
        selected_node = available_nodes[0]

        # Find available GPU instance
        available_gpu = self.db.query(GPUInstance).filter(
            GPUInstance.node_id == selected_node.id,
            GPUInstance.status == "available"
        ).first()

        if not available_gpu:
            return

        # Assign job to node and GPU
        job.assigned_node_id = selected_node.id
        job.assigned_gpu_id = available_gpu.id
        job.status = "scheduled"
        job.scheduled_at = datetime.utcnow()

        # Update GPU instance
        available_gpu.status = "busy"
        available_gpu.current_job_id = job.id

        # Update node job count
        selected_node.current_jobs += 1

        self.db.commit()

        # Submit job to node
        job_submission = JobSubmission(
            job_id=job.id,
            docker_image=job.docker_image,
            docker_tag=job.docker_tag,
            docker_registry=job.docker_registry,
            job_config=job.job_config,
            input_data=job.input_data,
            resource_requirements={
                "gpu_memory": job.gpu_memory_required,
                "cpu_cores": job.cpu_cores_required,
                "memory": job.memory_required,
                "storage": job.storage_required
            }
        )

        self.submit_job_to_node(selected_node.node_id, job_submission)

    def _calculate_job_cost(self, job: GPUJob) -> float:
        """Calculate job cost based on resource usage and duration"""
        if not job.assigned_node or not job.duration_seconds:
            return 0.0

        hours = job.duration_seconds / 3600.0
        cost = 0.0

        # GPU cost
        if job.gpu_memory_used and job.assigned_node.price_per_gpu_hour:
            gpu_hours = (job.gpu_memory_used / 1024) * hours  # Convert MB to GB
            cost += gpu_hours * job.assigned_node.price_per_gpu_hour

        # CPU cost
        if job.cpu_cores_used and job.assigned_node.price_per_cpu_hour:
            cost += job.cpu_cores_used * hours * job.assigned_node.price_per_cpu_hour

        # Memory cost
        if job.memory_used and job.assigned_node.price_per_memory_gb_hour:
            memory_gb_hours = (job.memory_used / 1024) * hours
            cost += memory_gb_hours * job.assigned_node.price_per_memory_gb_hour

        return cost
