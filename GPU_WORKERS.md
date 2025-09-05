# ImagePod GPU Workers System

A comprehensive Kubernetes-based GPU worker system that allows GPU servers to automatically register themselves and become available for job processing.

## 🚀 Features

### ✅ **Auto-Discovery & Registration**
- GPU nodes automatically register with the main API
- Worker agents run on each GPU node
- Real-time heartbeat monitoring
- Automatic resource discovery (GPU count, memory, CPU cores)

### ✅ **GPU-Aware Job Scheduling**
- Intelligent job scheduling based on GPU requirements
- Resource availability checking
- Automatic job assignment to available nodes
- Cost calculation based on resource usage

### ✅ **Kubernetes Integration**
- DaemonSet deployment for GPU workers
- GPU resource management
- Container orchestration
- Health checks and monitoring

### ✅ **Docker Container Execution**
- Run any Docker image on GPU nodes
- GPU memory and compute resource allocation
- Real-time job monitoring
- Automatic cleanup and resource management

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Main API      │    │  GPU Node 1     │    │  GPU Node 2     │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ GPU Worker  │ │◄──►│ │ Worker      │ │    │ │ Worker      │ │
│ │ Service     │ │    │ │ Agent       │ │    │ │ Agent       │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Job         │ │◄──►│ │ Docker      │ │    │ │ Docker      │ │
│ │ Scheduler   │ │    │ │ Containers  │ │    │ │ Containers  │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Components

### 1. **GPU Node Model**
- Represents physical GPU servers
- Tracks GPU specifications, resources, and status
- Manages pricing and billing information
- Kubernetes integration metadata

### 2. **Worker Agent**
- Runs on each GPU node
- Registers with main API
- Monitors GPU resources
- Executes Docker containers
- Reports job status

### 3. **Job Scheduler**
- Intelligent job assignment
- Resource requirement matching
- Cost optimization
- Load balancing across nodes

### 4. **Kubernetes Manifests**
- DaemonSet for automatic deployment
- Service definitions
- Resource quotas and limits
- Health checks

## 🛠️ Installation & Setup

### Prerequisites
- Kubernetes cluster with GPU nodes
- NVIDIA GPU drivers installed
- Docker registry access
- kubectl configured

### 1. Deploy GPU Workers

```bash
# Make deployment script executable
chmod +x scripts/deploy_gpu_workers.sh

# Deploy to Kubernetes
./scripts/deploy_gpu_workers.sh
```

### 2. Configure Registration Token

```bash
# Create registration token secret
kubectl create secret generic imagepod-secrets \
    --from-literal=registration-token="your-secure-token" \
    --namespace=imagepod
```

### 3. Verify Deployment

```bash
# Check GPU worker pods
kubectl get pods -n imagepod -l app=imagepod-gpu-worker

# Check GPU worker services
kubectl get services -n imagepod -l app=imagepod-gpu-worker

# View logs
kubectl logs -n imagepod -l app=imagepod-gpu-worker
```

## 🔧 API Usage

### Register GPU Node

```bash
curl -X POST "http://localhost:8000/gpu-workers/nodes/register" \
  -H "Content-Type: application/json" \
  -d '{
    "node_name": "gpu-server-1",
    "hostname": "gpu-server-1.local",
    "gpu_count": 2,
    "gpu_type": "RTX 4090",
    "gpu_memory_total": 24576,
    "cpu_cores": 16,
    "memory_total": 32768,
    "max_concurrent_jobs": 2
  }'
```

### Create GPU Job

```bash
curl -X POST "http://localhost:8000/gpu-workers/jobs/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "AI Training Job",
    "docker_image": "pytorch/pytorch",
    "docker_tag": "latest",
    "gpu_memory_required": 8192,
    "cpu_cores_required": 4,
    "memory_required": 16384,
    "input_data": {"dataset": "imagenet", "epochs": 100}
  }'
```

### Check Available Nodes

```bash
curl "http://localhost:8000/gpu-workers/available-nodes/?gpu_memory_required=4096"
```

### Update Node Heartbeat

```bash
curl -X POST "http://localhost:8000/gpu-workers/nodes/{node_id}/heartbeat" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "gpu-e5be90b5e5d6",
    "gpu_memory_available": 20000,
    "cpu_cores_available": 14,
    "current_jobs": 1,
    "health_status": "healthy"
  }'
```

## 📊 Monitoring

### Node Statistics

```bash
curl "http://localhost:8000/gpu-workers/nodes/{node_id}/stats"
```

### Job Status

```bash
curl "http://localhost:8000/gpu-workers/jobs/{job_id}"
```

### Worker Agent Status

```bash
curl "http://localhost:8000/gpu-workers/agents/{agent_id}"
```

## 🔄 Workflow

### 1. **Node Registration**
1. GPU node starts up
2. Worker agent registers with main API
3. Node capabilities and resources are discovered
4. Node becomes available for job scheduling

### 2. **Job Submission**
1. User submits GPU job with requirements
2. Scheduler finds available nodes
3. Job is assigned to best matching node
4. Docker container is deployed and executed

### 3. **Job Execution**
1. Worker agent pulls Docker image
2. Container runs with GPU access
3. Real-time monitoring and logging
4. Status updates sent to main API

### 4. **Job Completion**
1. Container execution completes
2. Results and logs are collected
3. Resources are freed up
4. Billing information is calculated

## 🎯 Use Cases

### **AI/ML Training**
- Distributed training across multiple GPUs
- Automatic scaling based on workload
- Cost optimization for long-running jobs

### **Inference Services**
- Real-time model inference
- Load balancing across GPU nodes
- Auto-scaling based on demand

### **Data Processing**
- GPU-accelerated data processing
- Batch job processing
- Resource-efficient scheduling

### **Research & Development**
- Experimental model training
- A/B testing different configurations
- Resource sharing across teams

## 🔒 Security

### **Authentication**
- JWT-based authentication for users
- API key authentication for worker agents
- Secure token-based node registration

### **Authorization**
- Role-based access control
- Resource isolation between users
- Secure container execution

### **Network Security**
- TLS encryption for API communication
- Network policies in Kubernetes
- Secure Docker registry access

## 📈 Scaling

### **Horizontal Scaling**
- Add more GPU nodes to cluster
- Automatic load distribution
- Dynamic resource allocation

### **Vertical Scaling**
- Increase GPU memory allocation
- CPU and RAM scaling
- Storage capacity management

### **Auto-Scaling**
- Kubernetes HPA integration
- Custom metrics-based scaling
- Cost-aware scaling policies

## 🐛 Troubleshooting

### **Common Issues**

1. **Node Registration Fails**
   - Check network connectivity
   - Verify registration token
   - Check API endpoint configuration

2. **Jobs Not Scheduling**
   - Verify node availability
   - Check resource requirements
   - Review job configuration

3. **Container Execution Fails**
   - Check Docker image availability
   - Verify GPU driver installation
   - Review container logs

### **Debug Commands**

```bash
# Check node status
kubectl describe nodes

# View worker agent logs
kubectl logs -n imagepod -l app=imagepod-gpu-worker

# Check GPU resources
kubectl top nodes

# View job status
kubectl get jobs -n imagepod
```

## 🚀 Next Steps

1. **Production Deployment**
   - Configure production Kubernetes cluster
   - Set up monitoring and alerting
   - Implement backup and recovery

2. **Advanced Features**
   - Multi-GPU job support
   - GPU memory sharing
   - Advanced scheduling algorithms

3. **Integration**
   - CI/CD pipeline integration
   - External monitoring systems
   - Third-party tool integration

## 📚 API Reference

### **GPU Workers API Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/gpu-workers/nodes/register` | Register GPU node |
| GET | `/gpu-workers/nodes/` | List GPU nodes |
| GET | `/gpu-workers/nodes/{node_id}` | Get GPU node details |
| POST | `/gpu-workers/nodes/{node_id}/heartbeat` | Update node heartbeat |
| GET | `/gpu-workers/nodes/{node_id}/stats` | Get node statistics |
| POST | `/gpu-workers/jobs/` | Create GPU job |
| GET | `/gpu-workers/jobs/` | List GPU jobs |
| GET | `/gpu-workers/jobs/{job_id}` | Get job details |
| POST | `/gpu-workers/jobs/{job_id}/status` | Update job status |
| GET | `/gpu-workers/available-nodes/` | Get available nodes |
| POST | `/gpu-workers/agents/register` | Register worker agent |

## 🎉 Success!

The GPU Workers system is now fully operational! You can:

- ✅ Deploy GPU workers to Kubernetes
- ✅ Register GPU nodes automatically
- ✅ Submit and execute GPU jobs
- ✅ Monitor resource usage and job status
- ✅ Scale horizontally and vertically
- ✅ Integrate with existing workflows

Your ImagePod platform now has a complete GPU worker system that can handle any GPU-intensive workload!
