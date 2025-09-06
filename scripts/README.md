# ImagePod Scripts

This directory contains simplified scripts for setting up and deploying ImagePod.

## 🚀 Quick Setup

### Master Node (Backend + Kubernetes Control Plane)
```bash
./scripts/setup_master.sh
```
This script:
- Installs Docker, Kubernetes, and all dependencies
- Initializes the Kubernetes cluster
- Deploys ImagePod backend services
- Provides the join command for worker nodes

### GPU Worker Node
```bash
./scripts/setup_worker.sh 'kubeadm join <master-ip>:6443 --token <token> --discovery-token-ca-cert-hash <hash>'
```
This script:
- Installs NVIDIA drivers (if not present)
- Installs Docker, Kubernetes, and GPU support
- Joins the cluster using the provided command
- Deploys GPU worker agent

## 📋 Other Scripts

### Deployment Scripts
- `deploy_full_kubernetes.sh` - Deploys all ImagePod services to Kubernetes
- `deploy_gpu_workers.sh` - Deploys GPU worker DaemonSet and services

### Utility Scripts
- `init_db.py` - Initialize the database with required tables and data
- `generate_secrets.sh` - Generates secure random strings for application secrets
- `validate_manifests.sh` - Validates Kubernetes YAML manifests locally
- `shutdown.sh` - **NEW: Completely shuts down and removes all ImagePod services**

## 🎯 Usage Examples

### Complete Setup (2 machines)

**On Master Node:**
```bash
# Clone the repository
git clone <your-repo>
cd imagepod

# Run master setup
./scripts/setup_master.sh

# Copy the join command from the output
```

**On GPU Worker Node:**
```bash
# Clone the repository
git clone <your-repo>
cd imagepod

# Run worker setup with join command
./scripts/setup_worker.sh 'kubeadm join 192.168.1.100:6443 --token abc123... --discovery-token-ca-cert-hash sha256:...'
```

### Check Status
```bash
# On master node
kubectl get nodes
kubectl get pods -n imagepod

# Access ImagePod API
kubectl port-forward -n imagepod svc/imagepod-api 8000:8000
```

### Shutdown Everything
```bash
# On any node (master or worker)
./scripts/shutdown.sh
```
**⚠️ Warning: This will completely remove all ImagePod services and data!**

## 🔧 Requirements

- **Master Node**: Ubuntu 20.04+, Debian 11+, or Arch Linux
- **Worker Node**: Ubuntu 20.04+, Debian 11+, or Arch Linux + NVIDIA GPU
- Internet connection
- sudo access

## 📝 Notes

- Scripts automatically detect the operating system
- GPU worker setup will prompt for reboot if NVIDIA drivers need installation
- All scripts include error handling and colored output
- The master script saves the join command to `/tmp/kubeadm-join-command.txt`

## 🔍 Troubleshooting

### Permission Issues
```bash
# Make scripts executable
chmod +x scripts/*.sh
```

### NVIDIA Driver Issues
```bash
# Check if NVIDIA drivers are installed
nvidia-smi

# If not installed, the worker script will install them and prompt for reboot
```

### Network Issues
```bash
# Check if ports are available
netstat -tulpn | grep :8000
netstat -tulpn | grep :6443
```

## 📖 Documentation

- [Deployment Guide](../DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [Kubernetes Setup](../KUBERNETES_FULL_INFRASTRUCTURE.md) - Kubernetes-specific setup
- [GPU Workers](../KUBERNETES_NODE_TYPES.md) - GPU worker system documentation