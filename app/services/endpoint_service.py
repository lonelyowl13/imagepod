from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.endpoint import Endpoint, EndpointDeployment
from app.models.job import Job
from app.schemas.endpoint import EndpointCreate, EndpointUpdate, EndpointJobRequest
from app.services.job_service import JobService
from app.services.billing_service import BillingService
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


class EndpointService:
    def __init__(self, db: Session):
        self.db = db
        self.job_service = JobService(db)
        self.billing_service = BillingService(db)
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

    def create_endpoint(self, user_id: int, endpoint_data: EndpointCreate) -> Endpoint:
        """Create a new endpoint"""
        # Generate endpoint ID if not provided
        endpoint_id = endpoint_data.endpoint_id or self._generate_endpoint_id()
        
        # Encrypt Docker credentials if provided
        docker_password = None
        docker_username = None
        if hasattr(endpoint_data, 'docker_password') and endpoint_data.docker_password:
            docker_password = self._encrypt_password(endpoint_data.docker_password)
        if hasattr(endpoint_data, 'docker_username') and endpoint_data.docker_username:
            docker_username = endpoint_data.docker_username
        
        db_endpoint = Endpoint(
            user_id=user_id,
            endpoint_id=endpoint_id,
            name=endpoint_data.name,
            description=endpoint_data.description,
            docker_image=endpoint_data.docker_image,
            docker_tag=endpoint_data.docker_tag,
            docker_registry=endpoint_data.docker_registry,
            docker_username=docker_username,
            docker_password=docker_password,
            endpoint_config=endpoint_data.endpoint_config,
            input_schema=endpoint_data.input_schema,
            output_schema=endpoint_data.output_schema,
            min_gpu_memory=endpoint_data.min_gpu_memory,
            max_gpu_memory=endpoint_data.max_gpu_memory,
            min_cpu_cores=endpoint_data.min_cpu_cores,
            max_cpu_cores=endpoint_data.max_cpu_cores,
            min_ram=endpoint_data.min_ram,
            max_ram=endpoint_data.max_ram,
            min_replicas=endpoint_data.min_replicas,
            max_replicas=endpoint_data.max_replicas,
            target_replicas=endpoint_data.target_replicas,
            auto_scaling=endpoint_data.auto_scaling,
            scale_up_threshold=endpoint_data.scale_up_threshold,
            scale_down_threshold=endpoint_data.scale_down_threshold,
            base_price_per_second=endpoint_data.base_price_per_second,
            deployment_type=endpoint_data.deployment_type,
            deployment_config=endpoint_data.deployment_config,
            is_public=endpoint_data.is_public,
            api_key_required=endpoint_data.api_key_required,
            rate_limit=endpoint_data.rate_limit,
            status="pending"
        )

        self.db.add(db_endpoint)
        self.db.commit()
        self.db.refresh(db_endpoint)

        # Deploy the endpoint
        self._deploy_endpoint(db_endpoint)

        return db_endpoint

    def get_endpoint(self, endpoint_id: str, user_id: Optional[int] = None) -> Optional[Endpoint]:
        """Get endpoint by endpoint_id"""
        query = self.db.query(Endpoint).filter(Endpoint.endpoint_id == endpoint_id)
        if user_id:
            query = query.filter(Endpoint.user_id == user_id)
        return query.first()

    def get_endpoint_by_id(self, endpoint_id: int, user_id: Optional[int] = None) -> Optional[Endpoint]:
        """Get endpoint by internal ID"""
        query = self.db.query(Endpoint).filter(Endpoint.id == endpoint_id)
        if user_id:
            query = query.filter(Endpoint.user_id == user_id)
        return query.first()

    def get_user_endpoints(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Endpoint]:
        """Get user's endpoints"""
        return (
            self.db.query(Endpoint)
            .filter(Endpoint.user_id == user_id)
            .order_by(desc(Endpoint.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_public_endpoints(self, skip: int = 0, limit: int = 100) -> List[Endpoint]:
        """Get public endpoints"""
        return (
            self.db.query(Endpoint)
            .filter(Endpoint.is_public == True, Endpoint.status == "active")
            .order_by(desc(Endpoint.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_endpoint(self, endpoint_id: int, endpoint_update: EndpointUpdate, user_id: Optional[int] = None) -> Optional[Endpoint]:
        """Update an endpoint"""
        endpoint = self.get_endpoint_by_id(endpoint_id, user_id)
        if not endpoint:
            return None

        update_data = endpoint_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(endpoint, field, value)

        endpoint.status = "pending"  # Mark for redeployment
        self.db.commit()
        self.db.refresh(endpoint)

        # Redeploy if necessary
        if any(field in update_data for field in ['docker_image', 'docker_tag', 'deployment_config']):
            self._deploy_endpoint(endpoint)

        return endpoint

    def delete_endpoint(self, endpoint_id: int, user_id: Optional[int] = None) -> bool:
        """Delete an endpoint"""
        endpoint = self.get_endpoint_by_id(endpoint_id, user_id)
        if not endpoint:
            return False

        # Terminate all deployments
        self._terminate_endpoint(endpoint)

        self.db.delete(endpoint)
        self.db.commit()
        return True

    def create_endpoint_job(self, endpoint_id: str, job_request: EndpointJobRequest, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Create a job for an endpoint"""
        endpoint = self.get_endpoint(endpoint_id, user_id)
        if not endpoint:
            return None

        if endpoint.status != "active":
            return {"error": "Endpoint is not active"}

        # Validate input against schema
        if endpoint.input_schema and not self._validate_input(job_request.input, endpoint.input_schema):
            return {"error": "Invalid input data"}

        # Create job
        from app.schemas.job import JobCreate
        job_data = JobCreate(
            name=f"Endpoint Job - {endpoint.name}",
            description=f"Job for endpoint {endpoint.endpoint_id}",
            input_data=job_request.input
        )

        job = self.job_service.create_job(user_id or endpoint.user_id, job_data)
        job.endpoint_id = endpoint.id
        self.db.commit()

        # Route to endpoint deployment
        deployment = self._get_available_deployment(endpoint)
        if deployment:
            job.worker_id = deployment.id  # Use deployment as worker
            job.status = "running"
            job.started_at = datetime.utcnow()
            self.db.commit()

            # Update endpoint stats
            endpoint.total_requests += 1

        return self._format_endpoint_job_response(job)

    def get_endpoint_job(self, endpoint_id: str, job_id: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get job status from endpoint"""
        endpoint = self.get_endpoint(endpoint_id, user_id)
        if not endpoint:
            return None

        job = self.job_service.get_job(int(job_id), user_id or endpoint.user_id)
        if not job or job.endpoint_id != endpoint.id:
            return None

        return self._format_endpoint_job_response(job)

    def scale_endpoint(self, endpoint_id: int, target_replicas: int, user_id: Optional[int] = None) -> bool:
        """Scale an endpoint"""
        endpoint = self.get_endpoint_by_id(endpoint_id, user_id)
        if not endpoint:
            return False

        if target_replicas < endpoint.min_replicas or target_replicas > endpoint.max_replicas:
            return False

        endpoint.target_replicas = target_replicas
        self.db.commit()

        # Scale deployments
        self._scale_endpoint_deployments(endpoint, target_replicas)
        return True

    def get_endpoint_stats(self, endpoint_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get endpoint statistics"""
        endpoint = self.get_endpoint_by_id(endpoint_id, user_id)
        if not endpoint:
            return None

        # Calculate stats
        success_rate = 0.0
        if endpoint.total_requests > 0:
            success_rate = endpoint.successful_requests / endpoint.total_requests

        avg_execution_time = 0.0
        if endpoint.successful_requests > 0:
            avg_execution_time = endpoint.total_execution_time / endpoint.successful_requests

        # Get current resource usage from deployments
        deployments = self.db.query(EndpointDeployment).filter(
            EndpointDeployment.endpoint_id == endpoint_id,
            EndpointDeployment.status == "active"
        ).all()

        cpu_usage = sum(d.cpu_usage for d in deployments) / len(deployments) if deployments else 0.0
        memory_usage = sum(d.memory_usage for d in deployments) / len(deployments) if deployments else 0.0
        gpu_usage = sum(d.gpu_usage for d in deployments) / len(deployments) if deployments else 0.0

        return {
            "total_requests": endpoint.total_requests,
            "successful_requests": endpoint.successful_requests,
            "failed_requests": endpoint.failed_requests,
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time,
            "total_execution_time": endpoint.total_execution_time,
            "current_replicas": endpoint.current_replicas,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "gpu_usage": gpu_usage
        }

    def _generate_endpoint_id(self) -> str:
        """Generate a unique endpoint ID"""
        return f"ep-{uuid.uuid4().hex[:12]}"

    def _encrypt_password(self, password: str) -> str:
        """Encrypt password for storage"""
        return self.cipher.encrypt(password.encode()).decode()

    def _decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt password from storage"""
        return self.cipher.decrypt(encrypted_password.encode()).decode()

    def _validate_input(self, input_data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate input data against JSON schema"""
        # Simple validation - in production, use jsonschema library
        try:
            if "required" in schema:
                for field in schema["required"]:
                    if field not in input_data:
                        return False
            return True
        except Exception:
            return False

    def _deploy_endpoint(self, endpoint: Endpoint):
        """Deploy an endpoint"""
        if endpoint.deployment_type == "kubernetes":
            self._deploy_k8s_endpoint(endpoint)
        elif endpoint.deployment_type == "docker":
            self._deploy_docker_endpoint(endpoint)
        else:
            # Serverless deployment
            self._deploy_serverless_endpoint(endpoint)

    def _deploy_k8s_endpoint(self, endpoint: Endpoint):
        """Deploy endpoint using Kubernetes"""
        if not self.k8s_client:
            endpoint.status = "error"
            self.db.commit()
            return

        try:
            deployment_id = f"endpoint-{endpoint.endpoint_id}-{uuid.uuid4().hex[:8]}"
            
            # Create deployment
            deployment_manifest = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": f"endpoint-{endpoint.endpoint_id}",
                    "labels": {
                        "app": "imagepod-endpoint",
                        "endpoint-id": endpoint.endpoint_id,
                        "user-id": str(endpoint.user_id)
                    }
                },
                "spec": {
                    "replicas": endpoint.target_replicas,
                    "selector": {
                        "matchLabels": {
                            "app": "imagepod-endpoint",
                            "endpoint-id": endpoint.endpoint_id
                        }
                    },
                    "template": {
                        "metadata": {
                            "labels": {
                                "app": "imagepod-endpoint",
                                "endpoint-id": endpoint.endpoint_id
                            }
                        },
                        "spec": {
                            "containers": [{
                                "name": "endpoint",
                                "image": f"{endpoint.docker_image}:{endpoint.docker_tag}",
                                "env": [
                                    {"name": "ENDPOINT_ID", "value": endpoint.endpoint_id},
                                    {"name": "USER_ID", "value": str(endpoint.user_id)},
                                    {"name": "API_ENDPOINT", "value": f"http://api:8000"}
                                ],
                                "resources": {
                                    "requests": {
                                        "memory": f"{endpoint.min_ram or 512}Mi",
                                        "cpu": str(endpoint.min_cpu_cores or 1)
                                    },
                                    "limits": {
                                        "memory": f"{endpoint.max_ram or 1024}Mi",
                                        "cpu": str(endpoint.max_cpu_cores or 2)
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

            # Create service
            service_manifest = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": f"endpoint-{endpoint.endpoint_id}",
                    "labels": {
                        "app": "imagepod-endpoint",
                        "endpoint-id": endpoint.endpoint_id
                    }
                },
                "spec": {
                    "selector": {
                        "app": "imagepod-endpoint",
                        "endpoint-id": endpoint.endpoint_id
                    },
                    "ports": [{
                        "port": 8000,
                        "targetPort": 8000
                    }]
                }
            }

            core_v1 = client.CoreV1Api(self.k8s_client)
            core_v1.create_namespaced_service(
                namespace="default",
                body=service_manifest
            )

            # Create deployment record
            deployment = EndpointDeployment(
                endpoint_id=endpoint.id,
                deployment_id=deployment_id,
                status="active",
                health_status="healthy"
            )
            self.db.add(deployment)

            endpoint.status = "active"
            endpoint.deployed_at = datetime.utcnow()
            endpoint.current_replicas = endpoint.target_replicas

        except Exception as e:
            print(f"Failed to deploy K8s endpoint: {e}")
            endpoint.status = "error"

        self.db.commit()

    def _deploy_docker_endpoint(self, endpoint: Endpoint):
        """Deploy endpoint using Docker"""
        if not self.docker_client:
            endpoint.status = "error"
            self.db.commit()
            return

        try:
            deployment_id = f"endpoint-{endpoint.endpoint_id}-{uuid.uuid4().hex[:8]}"
            
            # Create container
            container = self.docker_client.containers.run(
                image=f"{endpoint.docker_image}:{endpoint.docker_tag}",
                name=f"endpoint-{endpoint.endpoint_id}",
                environment={
                    "ENDPOINT_ID": endpoint.endpoint_id,
                    "USER_ID": str(endpoint.user_id),
                    "API_ENDPOINT": "http://api:8000"
                },
                detach=True,
                remove=True
            )

            # Create deployment record
            deployment = EndpointDeployment(
                endpoint_id=endpoint.id,
                deployment_id=deployment_id,
                container_id=container.id,
                status="active",
                health_status="healthy"
            )
            self.db.add(deployment)

            endpoint.status = "active"
            endpoint.deployed_at = datetime.utcnow()
            endpoint.current_replicas = 1

        except Exception as e:
            print(f"Failed to deploy Docker endpoint: {e}")
            endpoint.status = "error"

        self.db.commit()

    def _deploy_serverless_endpoint(self, endpoint: Endpoint):
        """Deploy endpoint as serverless function"""
        # This would integrate with serverless platforms like AWS Lambda, Google Cloud Functions, etc.
        endpoint.status = "active"
        endpoint.deployed_at = datetime.utcnow()
        endpoint.current_replicas = 0  # Serverless scales to zero
        self.db.commit()

    def _terminate_endpoint(self, endpoint: Endpoint):
        """Terminate all deployments for an endpoint"""
        deployments = self.db.query(EndpointDeployment).filter(
            EndpointDeployment.endpoint_id == endpoint.id,
            EndpointDeployment.status == "active"
        ).all()

        for deployment in deployments:
            if endpoint.deployment_type == "kubernetes":
                self._terminate_k8s_deployment(endpoint, deployment)
            elif endpoint.deployment_type == "docker":
                self._terminate_docker_deployment(deployment)

            deployment.status = "terminated"
            deployment.terminated_at = datetime.utcnow()

        endpoint.status = "inactive"
        endpoint.current_replicas = 0
        self.db.commit()

    def _terminate_k8s_deployment(self, endpoint: Endpoint, deployment: EndpointDeployment):
        """Terminate Kubernetes deployment"""
        try:
            apps_v1 = client.AppsV1Api(self.k8s_client)
            apps_v1.delete_namespaced_deployment(
                name=f"endpoint-{endpoint.endpoint_id}",
                namespace="default"
            )

            core_v1 = client.CoreV1Api(self.k8s_client)
            core_v1.delete_namespaced_service(
                name=f"endpoint-{endpoint.endpoint_id}",
                namespace="default"
            )
        except Exception as e:
            print(f"Failed to terminate K8s deployment: {e}")

    def _terminate_docker_deployment(self, deployment: EndpointDeployment):
        """Terminate Docker deployment"""
        try:
            if deployment.container_id:
                container = self.docker_client.containers.get(deployment.container_id)
                container.stop()
        except Exception as e:
            print(f"Failed to terminate Docker deployment: {e}")

    def _get_available_deployment(self, endpoint: Endpoint) -> Optional[EndpointDeployment]:
        """Get an available deployment for job execution"""
        return (
            self.db.query(EndpointDeployment)
            .filter(
                EndpointDeployment.endpoint_id == endpoint.id,
                EndpointDeployment.status == "active",
                EndpointDeployment.health_status == "healthy"
            )
            .first()
        )

    def _scale_endpoint_deployments(self, endpoint: Endpoint, target_replicas: int):
        """Scale endpoint deployments"""
        if endpoint.deployment_type == "kubernetes":
            self._scale_k8s_deployments(endpoint, target_replicas)
        elif endpoint.deployment_type == "docker":
            self._scale_docker_deployments(endpoint, target_replicas)

    def _scale_k8s_deployments(self, endpoint: Endpoint, target_replicas: int):
        """Scale Kubernetes deployments"""
        try:
            apps_v1 = client.AppsV1Api(self.k8s_client)
            deployment = apps_v1.read_namespaced_deployment(
                name=f"endpoint-{endpoint.endpoint_id}",
                namespace="default"
            )
            deployment.spec.replicas = target_replicas
            apps_v1.patch_namespaced_deployment(
                name=f"endpoint-{endpoint.endpoint_id}",
                namespace="default",
                body=deployment
            )
            endpoint.current_replicas = target_replicas
        except Exception as e:
            print(f"Failed to scale K8s deployment: {e}")

    def _scale_docker_deployments(self, endpoint: Endpoint, target_replicas: int):
        """Scale Docker deployments"""
        current_deployments = self.db.query(EndpointDeployment).filter(
            EndpointDeployment.endpoint_id == endpoint.id,
            EndpointDeployment.status == "active"
        ).count()

        if target_replicas > current_deployments:
            # Scale up
            for _ in range(target_replicas - current_deployments):
                self._deploy_docker_endpoint(endpoint)
        elif target_replicas < current_deployments:
            # Scale down
            deployments_to_terminate = self.db.query(EndpointDeployment).filter(
                EndpointDeployment.endpoint_id == endpoint.id,
                EndpointDeployment.status == "active"
            ).limit(current_deployments - target_replicas).all()

            for deployment in deployments_to_terminate:
                self._terminate_docker_deployment(deployment)
                deployment.status = "terminated"
                deployment.terminated_at = datetime.utcnow()

        endpoint.current_replicas = target_replicas
        self.db.commit()

    def _format_endpoint_job_response(self, job: Job) -> Dict[str, Any]:
        """Format job response for endpoint API"""
        return {
            "id": str(job.id),
            "status": job.status,
            "input": job.input_data,
            "output": job.output_data,
            "error": job.error_message,
            "executionTime": job.duration_seconds,
            "cost": job.cost,
            "createdAt": job.created_at.isoformat() if job.created_at else None,
            "startedAt": job.started_at.isoformat() if job.started_at else None,
            "completedAt": job.completed_at.isoformat() if job.completed_at else None,
        }
