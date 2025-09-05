from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.worker import Worker, WorkerPool
from app.models.job import Job
from app.schemas.worker import WorkerCreate, WorkerPoolCreate, WorkerStatusUpdate
import uuid
import docker
import kubernetes
from kubernetes import client, config
from app.config import settings
from datetime import datetime, timedelta
import asyncio
import httpx


class WorkerService:
    def __init__(self, db: Session):
        self.db = db
        self.docker_client = None
        self.k8s_client = None
        
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

    def create_worker_pool(self, pool_data: WorkerPoolCreate) -> WorkerPool:
        db_pool = WorkerPool(**pool_data.dict())
        
        self.db.add(db_pool)
        self.db.commit()
        self.db.refresh(db_pool)
        
        # Start initial workers if target_workers > 0
        if db_pool.target_workers > 0:
            self._scale_pool(db_pool.id, db_pool.target_workers)
        
        return db_pool

    def get_worker_pool(self, pool_id: int) -> Optional[WorkerPool]:
        return self.db.query(WorkerPool).filter(WorkerPool.id == pool_id).first()

    def get_worker_pools(self, skip: int = 0, limit: int = 100) -> List[WorkerPool]:
        return (
            self.db.query(WorkerPool)
            .filter(WorkerPool.is_active == True)
            .order_by(desc(WorkerPool.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_worker_pool(self, pool_id: int, update_data: Dict[str, Any]) -> Optional[WorkerPool]:
        pool = self.get_worker_pool(pool_id)
        if not pool:
            return None

        for field, value in update_data.items():
            if hasattr(pool, field):
                setattr(pool, field, value)

        self.db.commit()
        self.db.refresh(pool)
        return pool

    def delete_worker_pool(self, pool_id: int) -> bool:
        pool = self.get_worker_pool(pool_id)
        if not pool:
            return False

        # Terminate all workers in the pool
        workers = self.get_pool_workers(pool_id)
        for worker in workers:
            self.terminate_worker(worker.id)

        pool.is_active = False
        self.db.commit()
        return True

    def get_pool_workers(self, pool_id: int) -> List[Worker]:
        return (
            self.db.query(Worker)
            .filter(Worker.pool_id == pool_id)
            .all()
        )

    def create_worker(self, pool_id: int, worker_data: WorkerCreate) -> Worker:
        pool = self.get_worker_pool(pool_id)
        if not pool:
            raise ValueError("Worker pool not found")

        worker_id = str(uuid.uuid4())
        
        db_worker = Worker(
            pool_id=pool_id,
            worker_id=worker_id,
            name=worker_data.name,
            gpu_type=worker_data.gpu_type or pool.gpu_type,
            gpu_memory=worker_data.gpu_memory or pool.gpu_memory,
            cpu_cores=worker_data.cpu_cores or pool.cpu_cores,
            ram=worker_data.ram or pool.ram,
            storage=worker_data.storage or pool.storage,
            endpoint_url=worker_data.endpoint_url,
            metadata=worker_data.metadata,
            status="pending"
        )

        self.db.add(db_worker)
        self.db.commit()
        self.db.refresh(db_worker)

        # Deploy worker based on infrastructure type
        self._deploy_worker(db_worker, pool)

        return db_worker

    def get_worker(self, worker_id: int) -> Optional[Worker]:
        return self.db.query(Worker).filter(Worker.id == worker_id).first()

    def get_worker_by_external_id(self, external_worker_id: str) -> Optional[Worker]:
        return self.db.query(Worker).filter(Worker.worker_id == external_worker_id).first()

    def get_workers(self, skip: int = 0, limit: int = 100) -> List[Worker]:
        return (
            self.db.query(Worker)
            .order_by(desc(Worker.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_worker_status(self, worker_id: int, status_update: WorkerStatusUpdate) -> Optional[Worker]:
        worker = self.get_worker(worker_id)
        if not worker:
            return None

        update_data = status_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(worker, field, value)

        # Update heartbeat
        worker.last_heartbeat = datetime.utcnow()

        self.db.commit()
        self.db.refresh(worker)
        return worker

    def terminate_worker(self, worker_id: int) -> bool:
        worker = self.get_worker(worker_id)
        if not worker:
            return False

        # Terminate based on infrastructure type
        pool = self.get_worker_pool(worker.pool_id)
        if pool:
            self._terminate_worker_infrastructure(worker, pool)

        worker.status = "terminated"
        worker.terminated_at = datetime.utcnow()
        
        # Update pool worker count
        pool.current_workers = max(0, pool.current_workers - 1)

        self.db.commit()
        return True

    def find_available_worker(self, job: Job) -> Optional[Worker]:
        """Find an available worker that can handle the job"""
        # Get job requirements
        template = job.template
        if not template:
            return None

        # Find workers that match requirements
        query = self.db.query(Worker).filter(
            Worker.status == "idle",
            Worker.health_status == "healthy"
        )

        # Filter by resource requirements
        if template.min_gpu_memory:
            query = query.filter(Worker.gpu_memory >= template.min_gpu_memory)
        
        if template.min_cpu_cores:
            query = query.filter(Worker.cpu_cores >= template.min_cpu_cores)
        
        if template.min_ram:
            query = query.filter(Worker.ram >= template.min_ram)

        # Return the first available worker
        return query.first()

    def scale_pool(self, pool_id: int, target_workers: int) -> bool:
        """Scale a worker pool to target number of workers"""
        pool = self.get_worker_pool(pool_id)
        if not pool:
            return False

        # Ensure target is within limits
        target_workers = max(pool.min_workers, min(target_workers, pool.max_workers))
        
        return self._scale_pool(pool_id, target_workers)

    def _scale_pool(self, pool_id: int, target_workers: int) -> bool:
        """Internal method to scale worker pool"""
        pool = self.get_worker_pool(pool_id)
        if not pool:
            return False

        current_workers = self.db.query(Worker).filter(
            Worker.pool_id == pool_id,
            Worker.status.in_(["pending", "running", "idle"])
        ).count()

        if target_workers > current_workers:
            # Scale up
            workers_to_create = target_workers - current_workers
            for i in range(workers_to_create):
                worker_data = WorkerCreate(
                    name=f"{pool.name}-worker-{current_workers + i + 1}",
                    pool_id=pool_id
                )
                self.create_worker(pool_id, worker_data)
        
        elif target_workers < current_workers:
            # Scale down
            workers_to_terminate = current_workers - target_workers
            idle_workers = (
                self.db.query(Worker)
                .filter(
                    Worker.pool_id == pool_id,
                    Worker.status == "idle"
                )
                .limit(workers_to_terminate)
                .all()
            )
            
            for worker in idle_workers:
                self.terminate_worker(worker.id)

        pool.current_workers = target_workers
        pool.target_workers = target_workers
        self.db.commit()
        return True

    def auto_scale_pools(self):
        """Auto-scale all worker pools based on utilization"""
        pools = self.get_worker_pools()
        
        for pool in pools:
            if not pool.auto_scaling:
                continue

            # Get current utilization
            utilization = self._get_pool_utilization(pool.id)
            
            if utilization > pool.scale_up_threshold and pool.current_workers < pool.max_workers:
                # Scale up
                new_target = min(pool.current_workers + 1, pool.max_workers)
                self.scale_pool(pool.id, new_target)
            
            elif utilization < pool.scale_down_threshold and pool.current_workers > pool.min_workers:
                # Scale down
                new_target = max(pool.current_workers - 1, pool.min_workers)
                self.scale_pool(pool.id, new_target)

    def _get_pool_utilization(self, pool_id: int) -> float:
        """Get current utilization of a worker pool"""
        workers = self.get_pool_workers(pool_id)
        if not workers:
            return 0.0

        total_utilization = 0.0
        active_workers = 0

        for worker in workers:
            if worker.status in ["running", "idle"]:
                # Use GPU utilization as primary metric
                total_utilization += worker.gpu_utilization
                active_workers += 1

        return total_utilization / active_workers if active_workers > 0 else 0.0

    def _deploy_worker(self, worker: Worker, pool: WorkerPool):
        """Deploy worker based on infrastructure type"""
        if pool.infrastructure_type == "docker":
            self._deploy_docker_worker(worker, pool)
        elif pool.infrastructure_type == "kubernetes":
            self._deploy_k8s_worker(worker, pool)
        elif pool.infrastructure_type == "aws":
            self._deploy_aws_worker(worker, pool)

    def _deploy_docker_worker(self, worker: Worker, pool: WorkerPool):
        """Deploy worker using Docker"""
        if not self.docker_client:
            return

        try:
            # Create container
            container = self.docker_client.containers.run(
                image=f"{settings.docker_image_prefix}/worker:latest",
                name=f"worker-{worker.worker_id}",
                environment={
                    "WORKER_ID": worker.worker_id,
                    "POOL_ID": str(pool.id),
                    "API_ENDPOINT": worker.endpoint_url or "http://localhost:8000"
                },
                detach=True,
                remove=True
            )
            
            worker.container_id = container.id
            worker.status = "running"
            worker.started_at = datetime.utcnow()
            
        except Exception as e:
            print(f"Failed to deploy Docker worker: {e}")
            worker.status = "error"

    def _deploy_k8s_worker(self, worker: Worker, pool: WorkerPool):
        """Deploy worker using Kubernetes"""
        if not self.k8s_client:
            return

        try:
            # Create Kubernetes deployment
            # This is a simplified example - in production you'd want more sophisticated K8s manifests
            deployment_manifest = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": f"worker-{worker.worker_id}",
                    "labels": {
                        "app": "imagepod-worker",
                        "worker-id": worker.worker_id,
                        "pool-id": str(pool.id)
                    }
                },
                "spec": {
                    "replicas": 1,
                    "selector": {
                        "matchLabels": {
                            "app": "imagepod-worker",
                            "worker-id": worker.worker_id
                        }
                    },
                    "template": {
                        "metadata": {
                            "labels": {
                                "app": "imagepod-worker",
                                "worker-id": worker.worker_id
                            }
                        },
                        "spec": {
                            "containers": [{
                                "name": "worker",
                                "image": f"{settings.docker_image_prefix}/worker:latest",
                                "env": [
                                    {"name": "WORKER_ID", "value": worker.worker_id},
                                    {"name": "POOL_ID", "value": str(pool.id)},
                                    {"name": "API_ENDPOINT", "value": worker.endpoint_url or "http://localhost:8000"}
                                ],
                                "resources": {
                                    "requests": {
                                        "memory": f"{worker.ram}Mi",
                                        "cpu": str(worker.cpu_cores)
                                    },
                                    "limits": {
                                        "memory": f"{worker.ram}Mi",
                                        "cpu": str(worker.cpu_cores)
                                    }
                                }
                            }]
                        }
                    }
                }
            }

            # Apply deployment
            apps_v1 = client.AppsV1Api(self.k8s_client)
            apps_v1.create_namespaced_deployment(
                namespace="default",
                body=deployment_manifest
            )
            
            worker.status = "running"
            worker.started_at = datetime.utcnow()
            
        except Exception as e:
            print(f"Failed to deploy K8s worker: {e}")
            worker.status = "error"

    def _deploy_aws_worker(self, worker: Worker, pool: WorkerPool):
        """Deploy worker using AWS (EC2, ECS, etc.)"""
        # This would integrate with AWS services
        # For now, just mark as running
        worker.status = "running"
        worker.started_at = datetime.utcnow()

    def _terminate_worker_infrastructure(self, worker: Worker, pool: WorkerPool):
        """Terminate worker infrastructure"""
        if pool.infrastructure_type == "docker" and worker.container_id:
            try:
                container = self.docker_client.containers.get(worker.container_id)
                container.stop()
            except Exception as e:
                print(f"Failed to stop Docker container: {e}")
        
        elif pool.infrastructure_type == "kubernetes":
            try:
                apps_v1 = client.AppsV1Api(self.k8s_client)
                apps_v1.delete_namespaced_deployment(
                    name=f"worker-{worker.worker_id}",
                    namespace="default"
                )
            except Exception as e:
                print(f"Failed to delete K8s deployment: {e}")
        
        elif pool.infrastructure_type == "aws":
            # Terminate AWS resources
            pass

    async def health_check_workers(self):
        """Perform health checks on all workers"""
        workers = self.get_workers()
        
        for worker in workers:
            if worker.status not in ["running", "idle"]:
                continue
            
            # Check if worker is responding
            if worker.endpoint_url:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{worker.endpoint_url}/health", timeout=5.0)
                        if response.status_code == 200:
                            worker.health_status = "healthy"
                        else:
                            worker.health_status = "unhealthy"
                except Exception:
                    worker.health_status = "unhealthy"
            
            # Check if worker hasn't sent heartbeat recently
            if worker.last_heartbeat:
                time_since_heartbeat = datetime.utcnow() - worker.last_heartbeat
                if time_since_heartbeat > timedelta(minutes=5):
                    worker.health_status = "unhealthy"
            
            self.db.commit()
