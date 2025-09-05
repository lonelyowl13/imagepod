# ImagePod Deployment Guide

This guide explains how to deploy ImagePod in different configurations, from simple single-server setups to distributed GPU worker clusters.

## 🏗️ **Architecture Options**

### **Option 1: Simple Backend + GPU Workers (Recommended)**
- **Backend Server**: Simple server (no GPU) - runs the main ImagePod API
- **GPU Worker Servers**: GPU servers - run GPU workers via Docker

### **Option 2: All-in-One (Single Server)**
- **Single Server**: GPU server running both backend and GPU workers

### **Option 3: Kubernetes Cluster (Production)**
- **Backend Server**: Simple server - runs the main ImagePod API
- **GPU Worker Cluster**: Kubernetes cluster with GPU workers

## 🚀 **Option 1: Simple Backend + GPU Workers (Recommended)**

This is the easiest setup for most users. You don't need Kubernetes on the backend server.

### **Backend Server Setup (No GPU Required)**

On your simple server (no GPU):

```bash
# Run the backend setup script
./scripts/setup_backend_only.sh

# Edit configuration
sudo nano /opt/imagepod/.env

# Start the backend service
sudo systemctl start imagepod

# Check status
sudo systemctl status imagepod
```

**What this installs:**
- ✅ Docker and Docker Compose
- ✅ ImagePod backend API
- ✅ PostgreSQL database
- ✅ Redis cache
- ✅ Systemd service for auto-start

### **GPU Worker Server Setup**

On each GPU server:

```bash
# Set environment variables
export API_ENDPOINT="http://your-backend-server:8000"
export REGISTRATION_TOKEN="your-secure-token"

# Run the GPU worker setup script
./scripts/setup_gpu_worker_simple.sh

# Edit configuration
nano /opt/imagepod-gpu-worker/.env

# Start the GPU worker service
sudo systemctl start imagepod-gpu-worker

# Check status
sudo systemctl status imagepod-gpu-worker
```

**What this installs:**
- ✅ Docker with NVIDIA support
- ✅ NVIDIA drivers and Container Toolkit
- ✅ ImagePod GPU worker agent
- ✅ Systemd service for auto-start

### **Network Configuration**

Make sure your servers can communicate:

```bash
# On backend server, allow incoming connections
sudo ufw allow 8000/tcp

# On GPU worker servers, allow outgoing connections
sudo ufw allow out 8000/tcp
```

## 🎯 **Option 2: All-in-One (Single Server)**

If you have a single GPU server and want to run everything on it:

```bash
# Run the full Kubernetes setup
./scripts/setup_kubernetes.sh

# Deploy both backend and GPU workers
./scripts/deploy_gpu_workers.sh
```

## 🏢 **Option 3: Kubernetes Cluster (Production)**

For production environments with multiple GPU servers:

### **Backend Server (No Kubernetes)**
```bash
./scripts/setup_backend_only.sh
```

### **GPU Worker Cluster (Kubernetes)**
On each GPU server:
```bash
./scripts/setup_kubernetes.sh
```

Then deploy GPU workers:
```bash
./scripts/deploy_gpu_workers.sh
```

## 📋 **Quick Start (Option 1 - Recommended)**

### **Step 1: Setup Backend Server**

```bash
# On your simple server (no GPU)
git clone <your-imagepod-repo>
cd imagepod
./scripts/setup_backend_only.sh

# Configure the service
sudo nano /opt/imagepod/.env
# Set your database passwords, API keys, etc.

# Start the service
sudo systemctl start imagepod

# Verify it's running
curl http://localhost:8000/health
```

### **Step 2: Setup GPU Worker Server**

```bash
# On your GPU server
git clone <your-imagepod-repo>
cd imagepod

# Set your backend server address
export API_ENDPOINT="http://your-backend-server:8000"
export REGISTRATION_TOKEN="your-secure-token"

# Setup GPU worker
./scripts/setup_gpu_worker_simple.sh

# Configure the worker
nano /opt/imagepod-gpu-worker/.env
# Set API_ENDPOINT and REGISTRATION_TOKEN

# Start the worker
sudo systemctl start imagepod-gpu-worker

# Verify it's running
curl http://localhost:8080/health
```

### **Step 3: Test the System**

```bash
# On backend server, check if GPU worker registered
curl http://localhost:8000/gpu-workers/nodes/

# Create a test GPU job
curl -X POST "http://localhost:8000/gpu-workers/jobs/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "Test Job",
    "docker_image": "nvidia/cuda",
    "docker_tag": "11.8-runtime",
    "gpu_memory_required": 1024
  }'
```

## 🔧 **Configuration**

### **Backend Configuration (.env)**

```bash
# Database
POSTGRES_DB=imagepod
POSTGRES_USER=imagepod
POSTGRES_PASSWORD=your-secure-password

# Redis
REDIS_PASSWORD=your-redis-password

# API
SECRET_KEY=your-secret-key
API_HOST=0.0.0.0
API_PORT=8000

# Billing (optional)
STRIPE_SECRET_KEY=your-stripe-key
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key
```

### **GPU Worker Configuration (.env)**

```bash
# Backend connection
API_ENDPOINT=http://your-backend-server:8000
REGISTRATION_TOKEN=your-secure-token

# Worker settings
NODE_NAME=your-gpu-server
LOG_LEVEL=INFO
HEARTBEAT_INTERVAL=30
MAX_CONCURRENT_JOBS=1
WORKER_PORT=8080
```

## 🔍 **Monitoring & Management**

### **Backend Server**

```bash
# Check service status
sudo systemctl status imagepod

# View logs
sudo journalctl -u imagepod -f

# Check API health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

### **GPU Worker Server**

```bash
# Check service status
sudo systemctl status imagepod-gpu-worker

# View logs
sudo journalctl -u imagepod-gpu-worker -f

# Check GPU status
nvidia-smi

# Check worker health
curl http://localhost:8080/health

# View worker status
curl http://localhost:8080/status
```

## 🐛 **Troubleshooting**

### **Backend Issues**

```bash
# Check if service is running
sudo systemctl status imagepod

# Check Docker containers
docker-compose ps

# Check logs
docker-compose logs -f

# Restart service
sudo systemctl restart imagepod
```

### **GPU Worker Issues**

```bash
# Check if service is running
sudo systemctl status imagepod-gpu-worker

# Check GPU detection
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.8-runtime nvidia-smi

# Check worker logs
docker-compose logs -f

# Restart service
sudo systemctl restart imagepod-gpu-worker
```

### **Network Issues**

```bash
# Test connectivity between servers
curl http://your-backend-server:8000/health

# Check firewall rules
sudo ufw status

# Test port connectivity
telnet your-backend-server 8000
```

## 📊 **Scaling**

### **Add More GPU Workers**

To add more GPU servers:

1. Run the GPU worker setup script on each new server
2. Configure the same API_ENDPOINT and REGISTRATION_TOKEN
3. Start the service
4. The worker will automatically register with the backend

### **Load Balancing**

For high availability, you can:

1. Set up multiple backend servers behind a load balancer
2. Use a shared database (PostgreSQL cluster)
3. Use a shared Redis cluster for caching

## 🔒 **Security**

### **Network Security**

```bash
# On backend server
sudo ufw allow 8000/tcp
sudo ufw deny 22/tcp  # Disable SSH if not needed

# On GPU worker servers
sudo ufw allow out 8000/tcp
sudo ufw allow 8080/tcp  # For worker API
```

### **Authentication**

- Use strong REGISTRATION_TOKEN for worker authentication
- Set up proper API authentication for users
- Use HTTPS in production
- Regularly rotate secrets

## 🎉 **Success!**

Once everything is set up, you should have:

- ✅ Backend API running on your simple server
- ✅ GPU workers running on your GPU servers
- ✅ Automatic worker registration and discovery
- ✅ GPU job scheduling and execution
- ✅ Real-time monitoring and status updates

Your ImagePod system is now ready to process GPU-intensive workloads!

## 📚 **Next Steps**

1. **Test the system** with sample GPU jobs
2. **Monitor performance** and resource usage
3. **Scale up** by adding more GPU workers
4. **Set up monitoring** and alerting
5. **Configure backups** for your database
6. **Set up SSL/TLS** for production use
