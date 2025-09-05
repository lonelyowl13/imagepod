# Kubernetes Setup Guide for ImagePod GPU Workers

This guide will help you set up a Kubernetes cluster with GPU support on your server for running ImagePod GPU workers.

## 🎯 Prerequisites

### Hardware Requirements
- **GPU**: NVIDIA GPU with CUDA support (RTX 4090, A100, H100, etc.)
- **CPU**: Minimum 2 cores, recommended 4+ cores
- **RAM**: Minimum 4GB, recommended 8GB+
- **Storage**: Minimum 20GB free space
- **Network**: Internet connection for downloading packages

### Software Requirements
- **OS**: Ubuntu 20.04+ or Debian 11+
- **User**: Non-root user with sudo privileges
- **Internet**: Stable internet connection

## 🚀 Quick Setup (Automated)

### 1. Run the Setup Script

```bash
# Make the script executable
chmod +x scripts/setup_kubernetes.sh

# Run the setup script
./scripts/setup_kubernetes.sh
```

The script will automatically:
- Install Docker and containerd
- Install NVIDIA drivers and Container Toolkit
- Install Kubernetes components (kubeadm, kubelet, kubectl)
- Configure the system for Kubernetes
- Initialize a single-node cluster
- Install Flannel CNI
- Install NVIDIA Device Plugin
- Create ImagePod namespace

### 2. Reboot Your System

```bash
sudo reboot
```

### 3. Verify Installation

After reboot, verify everything is working:

```bash
# Check GPU detection
nvidia-smi

# Check Kubernetes cluster
kubectl get nodes

# Check GPU resources
kubectl describe nodes | grep -A 5 "Allocated resources"
```

### 4. Deploy ImagePod GPU Workers

```bash
# Deploy GPU workers
./deploy_imagepod_gpu_workers.sh
```

## 🔧 Manual Setup (Step by Step)

If you prefer to set up manually or need to troubleshoot:

### 1. Install Docker

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
```

### 2. Install NVIDIA Drivers

```bash
# Add NVIDIA repository
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt-get update

# Install NVIDIA drivers
sudo apt-get install -y nvidia-driver-535

# Reboot to load drivers
sudo reboot
```

### 3. Install NVIDIA Container Toolkit

```bash
# Add NVIDIA Container Toolkit repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install NVIDIA Container Toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure containerd
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

### 4. Install Kubernetes Components

```bash
# Add Kubernetes repository
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

# Install Kubernetes components
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

### 5. Configure System for Kubernetes

```bash
# Disable swap
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Configure kernel parameters
sudo tee /etc/modules-load.d/k8s.conf <<EOF
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

# Configure sysctl
sudo tee /etc/sysctl.d/k8s.conf <<EOF
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system
```

### 6. Configure containerd

```bash
sudo mkdir -p /etc/containerd
sudo tee /etc/containerd/config.toml <<EOF
version = 2
[plugins."io.containerd.grpc.v1.cri"]
  [plugins."io.containerd.grpc.v1.cri".containerd]
    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes]
      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
        runtime_type = "io.containerd.runc.v2"
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
          SystemdCgroup = true
      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
        runtime_type = "io.containerd.runc.v2"
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
          BinaryName = "nvidia-container-runtime"
          SystemdCgroup = true
EOF

sudo systemctl restart containerd
sudo systemctl enable containerd
```

### 7. Initialize Kubernetes Cluster

```bash
# Initialize cluster
sudo kubeadm init \
    --pod-network-cidr=10.244.0.0/16 \
    --cri-socket=unix:///var/run/containerd/containerd.sock \
    --kubernetes-version=v1.28.0

# Configure kubectl for current user
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### 8. Install Flannel CNI

```bash
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

### 9. Install NVIDIA Device Plugin

```bash
# Install NVIDIA Device Plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml

# Wait for device plugin to be ready
kubectl wait --for=condition=Ready pod -l name=nvidia-device-plugin-ds -n kube-system --timeout=300s
```

### 10. Label Node for GPU Workloads

```bash
# Get node name
NODE_NAME=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')

# Label node for GPU workloads
kubectl label node $NODE_NAME accelerator=nvidia-tesla-gpu
```

## 🔍 Verification

### Check GPU Detection

```bash
# Check NVIDIA driver
nvidia-smi

# Expected output:
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 535.xx.xx    Driver Version: 535.xx.xx    CUDA Version: 12.2  |
# |-------------------------------+----------------------+----------------------+
# | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
# | Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
# |                               |                      |               MIG M. |
# |===============================+======================+======================|
# |   0  NVIDIA GeForce ...  Off  | 00000000:01:00.0 Off |                  N/A |
# |  0%   45C    P8    15W / 450W |      0MiB / 24576MiB |      0%      Default |
# +-------------------------------+----------------------+----------------------+
```

### Check Kubernetes Cluster

```bash
# Check cluster status
kubectl get nodes

# Expected output:
# NAME     STATUS   ROLES           AGE   VERSION
# server   Ready    control-plane   5m    v1.28.0
```

### Check GPU Resources

```bash
# Check GPU resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# Expected output:
# Allocated resources:
#   (Total limits may be over 100 percent, i.e., overcommitted.)
#   Resource           Requests    Limits
#   --------           --------    ------
#   cpu                100m (2%)   0 (0%)
#   memory             128Mi (1%)  0 (0%)
#   ephemeral-storage  0 (0%)      0 (0%)
#   nvidia.com/gpu     0           0
```

### Check NVIDIA Device Plugin

```bash
# Check device plugin status
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds

# Expected output:
# NAME                        READY   STATUS    RESTARTS   AGE
# nvidia-device-plugin-ds-xxx 1/1     Running   0          2m
```

## 🚀 Deploy ImagePod GPU Workers

### 1. Create Namespace

```bash
kubectl create namespace imagepod
```

### 2. Create Secrets

```bash
kubectl create secret generic imagepod-secrets \
    --from-literal=registration-token="your-secure-token-here" \
    --from-literal=api-key="your-api-key-here" \
    --namespace=imagepod
```

### 3. Deploy GPU Workers

```bash
# Deploy GPU worker DaemonSet
kubectl apply -f k8s/gpu-worker-daemonset.yaml

# Deploy GPU worker services
kubectl apply -f k8s/gpu-worker-service.yaml
```

### 4. Verify Deployment

```bash
# Check GPU worker pods
kubectl get pods -n imagepod -l app=imagepod-gpu-worker

# Check logs
kubectl logs -n imagepod -l app=imagepod-gpu-worker

# Check services
kubectl get services -n imagepod -l app=imagepod-gpu-worker
```

## 🐛 Troubleshooting

### Common Issues

#### 1. **NVIDIA Driver Not Detected**

```bash
# Check if NVIDIA driver is loaded
lsmod | grep nvidia

# Check GPU detection
lspci | grep -i nvidia

# Reinstall NVIDIA drivers
sudo apt-get purge nvidia-*
sudo apt-get autoremove
sudo apt-get install nvidia-driver-535
sudo reboot
```

#### 2. **Kubernetes Cluster Not Ready**

```bash
# Check cluster status
kubectl get nodes

# Check kubelet logs
sudo journalctl -u kubelet -f

# Reset cluster if needed
sudo kubeadm reset
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
```

#### 3. **GPU Resources Not Available**

```bash
# Check NVIDIA Device Plugin
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds

# Check device plugin logs
kubectl logs -n kube-system -l name=nvidia-device-plugin-ds

# Restart device plugin
kubectl delete pods -n kube-system -l name=nvidia-device-plugin-ds
```

#### 4. **Container Runtime Issues**

```bash
# Check containerd status
sudo systemctl status containerd

# Check containerd logs
sudo journalctl -u containerd -f

# Restart containerd
sudo systemctl restart containerd
```

### Debug Commands

```bash
# Check system resources
htop
nvidia-smi
df -h

# Check Kubernetes resources
kubectl get nodes -o wide
kubectl get pods -A
kubectl describe nodes

# Check GPU worker logs
kubectl logs -n imagepod -l app=imagepod-gpu-worker --tail=50

# Check API connectivity
curl -k https://localhost:6443/version
```

## 📚 Additional Resources

### Documentation
- [Kubernetes Installation Guide](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/kubernetes/install-k8s.html)
- [Kubernetes GPU Support](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)

### Useful Commands

```bash
# Check cluster info
kubectl cluster-info

# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods -A

# Check GPU usage
kubectl describe nodes | grep -A 10 "nvidia.com/gpu"

# Port forward to access services
kubectl port-forward -n imagepod svc/imagepod-gpu-worker 8080:8080
```

## 🎉 Success!

Once everything is set up correctly, you should have:

- ✅ Kubernetes cluster running
- ✅ NVIDIA GPU detected and available
- ✅ NVIDIA Device Plugin installed
- ✅ ImagePod GPU workers deployed
- ✅ GPU resources available for scheduling

Your server is now ready to run GPU-intensive workloads through ImagePod!
