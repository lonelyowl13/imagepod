# ImagePod Setup Scripts

This directory contains setup scripts for deploying ImagePod in different configurations.

## 📋 **Available Scripts**

### **Backend Setup**
- `setup_backend_only.sh` - Sets up ImagePod backend on a simple server (no GPU required)

### **GPU Worker Setup**
- `setup_gpu_worker_simple.sh` - Sets up GPU worker on a GPU server using Docker
- `setup_kubernetes.sh` - Sets up Kubernetes cluster with GPU support

### **Deployment Scripts**
- `deploy_gpu_workers.sh` - Deploys GPU workers to Kubernetes
- `init_db.py` - Initializes the database

## 🚀 **Quick Start**

### **Option 1: Simple Backend + GPU Workers (Recommended)**

1. **Backend Server (No GPU)**
   ```bash
   ./scripts/setup_backend_only.sh
   ```

2. **GPU Worker Server**
   ```bash
   export API_ENDPOINT="http://your-backend-server:8000"
   export REGISTRATION_TOKEN="your-secure-token"
   ./scripts/setup_gpu_worker_simple.sh
   ```

### **Option 2: Kubernetes Cluster**

1. **Backend Server (No GPU)**
   ```bash
   ./scripts/setup_backend_only.sh
   ```

2. **GPU Worker Cluster**
   ```bash
   ./scripts/setup_kubernetes.sh
   ./scripts/deploy_gpu_workers.sh
   ```

## 🔧 **Script Features**

### **Automatic Path Detection**
All scripts automatically detect their location and work from any directory:
- No hardcoded paths
- Works when cloned to any location
- Portable across different systems

### **Environment Configuration**
Scripts create configuration files with sensible defaults:
- `.env` files for environment variables
- Docker Compose configurations
- Systemd service files

### **Error Handling**
- Comprehensive error checking
- Colored output for better readability
- Graceful failure handling

## 📁 **What Each Script Does**

### **setup_backend_only.sh**
- Installs Docker and Docker Compose
- Copies ImagePod files to `/opt/imagepod`
- Creates systemd service
- Sets up environment configuration

### **setup_gpu_worker_simple.sh**
- Installs Docker with NVIDIA support
- Installs NVIDIA drivers and Container Toolkit
- Copies worker agent files to `/opt/imagepod-gpu-worker`
- Creates systemd service for GPU worker

### **setup_kubernetes.sh**
- Installs Kubernetes components
- Configures NVIDIA GPU support
- Sets up cluster networking
- Installs NVIDIA Device Plugin

## 🔍 **Troubleshooting**

### **Permission Issues**
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run with sudo if needed
sudo ./scripts/setup_backend_only.sh
```

### **Path Issues**
Scripts automatically detect their location, but if you encounter issues:
```bash
# Run from project root
cd /path/to/imagepod
./scripts/setup_backend_only.sh
```

### **Network Issues**
```bash
# Check internet connectivity
ping google.com

# Check if ports are available
netstat -tulpn | grep :8000
```

## 📚 **Configuration**

### **Environment Variables**
Set these before running GPU worker setup:
```bash
export API_ENDPOINT="http://your-backend-server:8000"
export REGISTRATION_TOKEN="your-secure-token"
export WORKER_PORT="8080"
```

### **Custom Configuration**
Edit configuration files after setup:
```bash
# Backend configuration
sudo nano /opt/imagepod/.env

# GPU worker configuration
nano /opt/imagepod-gpu-worker/.env
```

## 🎯 **Next Steps**

After running the setup scripts:

1. **Configure your environment** - Edit `.env` files
2. **Start services** - Use systemctl commands
3. **Test the system** - Check health endpoints
4. **Monitor logs** - Use journalctl or docker logs

## 📖 **Documentation**

- [Deployment Guide](../DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [Kubernetes Setup](../KUBERNETES_SETUP.md) - Kubernetes-specific setup
- [GPU Workers](../GPU_WORKERS.md) - GPU worker system documentation
