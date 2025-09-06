# ImagePod Kubernetes Node Types Guide

This guide explains the different types of Kubernetes nodes needed for ImagePod and how to set them up correctly.

## 🏗️ **Node Types Overview**

### **Master Node (Control Plane)**
- **Purpose**: Runs Kubernetes control plane components
- **GPU**: ❌ No GPU needed
- **Script**: `setup_kubernetes_master.sh`
- **Services**: API server, etcd, scheduler, controller manager

### **Worker Node (No GPU)**
- **Purpose**: Runs backend services (API, database, Redis)
- **GPU**: ❌ No GPU needed
- **Script**: `setup_kubernetes_worker_no_gpu.sh`
- **Services**: PostgreSQL, Redis, ImagePod API, monitoring

### **Worker Node (With GPU)**
- **Purpose**: Runs GPU workers and executes GPU jobs
- **GPU**: ✅ NVIDIA GPU required
- **Script**: `setup_kubernetes_worker.sh`
- **Services**: GPU worker agents, Docker containers with GPU access

## 🚀 **Deployment Process**

### **Step 1: Set up Master Node**

On your master node (no GPU needed):

```bash
# Set up Kubernetes master
./scripts/setup_kubernetes_master.sh

# Note the kubeadm join command from the output
# Example: kubeadm join 10.0.0.100:6443 --token abc123... --discovery-token-ca-cert-hash sha256:...
```

### **Step 2: Set up Worker Nodes**

#### **For Backend Services (No GPU)**
On nodes that will run backend services:

```bash
# Set up Kubernetes worker (no GPU)
./scripts/setup_kubernetes_worker_no_gpu.sh

# Join the cluster using the command from master
sudo kubeadm join 10.0.0.100:6443 --token abc123... --discovery-token-ca-cert-hash sha256:...
```

#### **For GPU Workers (With GPU)**
On nodes with NVIDIA GPUs:

```bash
# Set up Kubernetes worker (with GPU)
./scripts/setup_kubernetes_worker.sh

# Reboot to load NVIDIA drivers
sudo reboot

# After reboot, join the cluster
sudo kubeadm join 10.0.0.100:6443 --token abc123... --discovery-token-ca-cert-hash sha256:...

# Label the node for GPU workloads
kubectl label node <node-name> accelerator=nvidia-tesla-gpu
```

### **Step 3: Deploy ImagePod**

```bash
# Deploy the full infrastructure
./scripts/deploy_full_kubernetes.sh
```

## 📋 **Node Configuration Details**

### **Master Node Configuration**

**What it installs:**
- ✅ Docker and containerd
- ✅ Kubernetes components (kubeadm, kubelet, kubectl)
- ✅ Flannel CNI
- ✅ **NO NVIDIA drivers or GPU support**

**What it does:**
- ✅ Initializes the Kubernetes cluster
- ✅ Configures kubectl for the current user
- ✅ Removes taint to allow pod scheduling
- ✅ Creates ImagePod namespace

### **Worker Node (No GPU) Configuration**

**What it installs:**
- ✅ Docker and containerd
- ✅ Kubernetes components (kubeadm, kubelet, kubectl)
- ✅ **NO NVIDIA drivers or GPU support**

**What it does:**
- ✅ Joins the Kubernetes cluster
- ✅ Runs backend services (API, database, Redis)
- ✅ Handles non-GPU workloads

### **Worker Node (With GPU) Configuration**

**What it installs:**
- ✅ Docker and containerd
- ✅ Kubernetes components (kubeadm, kubelet, kubectl)
- ✅ **NVIDIA drivers and Container Toolkit**
- ✅ **GPU support for containers**

**What it does:**
- ✅ Joins the Kubernetes cluster
- ✅ Runs GPU worker agents
- ✅ Executes GPU-intensive workloads
- ✅ Manages GPU resources

## 🔧 **Containerd Configuration Differences**

### **Master Node & Worker (No GPU)**
```toml
version = 2
[plugins."io.containerd.grpc.v1.cri"]
  [plugins."io.containerd.grpc.v1.cri".containerd]
    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes]
      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
        runtime_type = "io.containerd.runc.v2"
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
          SystemdCgroup = true
```

### **Worker Node (With GPU)**
```toml
version = 2
[plugins."io.containerd.grpc.v1.cri"]
  [plugins."io.containerd.grpc.v1.cri".containerd]
    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes]
      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
        runtime_type = "io.containerd.runc.v2"
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
          SystemdCgroup = true
      [plugins."io.containerd.grpc.v1.cri"].containerd.runtimes.nvidia]
        runtime_type = "io.containerd.runc.v2"
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
          BinaryName = "nvidia-container-runtime"
          SystemdCgroup = true
```

## 🎯 **Recommended Node Allocation**

### **Minimum Setup (3 Nodes)**
- **1 Master Node** - Control plane (no GPU)
- **1 Worker Node** - Backend services (no GPU)
- **1 Worker Node** - GPU workers (with GPU)

### **Production Setup (5+ Nodes)**
- **1 Master Node** - Control plane (no GPU)
- **2 Worker Nodes** - Backend services (no GPU)
- **2+ Worker Nodes** - GPU workers (with GPU)

### **High Availability Setup (7+ Nodes)**
- **3 Master Nodes** - Control plane (no GPU)
- **3 Worker Nodes** - Backend services (no GPU)
- **3+ Worker Nodes** - GPU workers (with GPU)

## 🔍 **Verification Commands**

### **Check Cluster Status**
```bash
# Check all nodes
kubectl get nodes

# Check node roles
kubectl get nodes --show-labels

# Check GPU resources
kubectl describe nodes | grep -A 5 "Allocated resources"
```

### **Check GPU Nodes**
```bash
# List GPU nodes
kubectl get nodes -l accelerator=nvidia-tesla-gpu

# Check GPU device plugin
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds

# Test GPU access
kubectl run gpu-test --rm -i --tty --restart=Never --image=nvidia/cuda:11.8-runtime --limits=nvidia.com/gpu=1 -- nvidia-smi
```

### **Check Backend Services**
```bash
# Check ImagePod pods
kubectl get pods -n imagepod

# Check services
kubectl get services -n imagepod

# Check logs
kubectl logs -n imagepod -l app=imagepod-api
```

## 🐛 **Troubleshooting**

### **Common Issues**

#### **1. GPU Node Not Detected**
```bash
# Check if NVIDIA drivers are loaded
nvidia-smi

# Check if node is labeled
kubectl get nodes --show-labels | grep accelerator

# Label the node
kubectl label node <node-name> accelerator=nvidia-tesla-gpu
```

#### **2. GPU Device Plugin Not Working**
```bash
# Check device plugin status
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds

# Check device plugin logs
kubectl logs -n kube-system -l name=nvidia-device-plugin-ds

# Restart device plugin
kubectl delete pods -n kube-system -l name=nvidia-device-plugin-ds
```

#### **3. Backend Services Not Starting**
```bash
# Check pod status
kubectl get pods -n imagepod

# Check pod logs
kubectl logs -n imagepod <pod-name>

# Check events
kubectl get events -n imagepod
```

## 📚 **Script Comparison**

| Script | GPU Support | NVIDIA Drivers | Container Toolkit | Use Case |
|--------|-------------|----------------|-------------------|----------|
| `setup_kubernetes_master.sh` | ❌ | ❌ | ❌ | Master node |
| `setup_kubernetes_worker_no_gpu.sh` | ❌ | ❌ | ❌ | Backend services |
| `setup_kubernetes_worker.sh` | ✅ | ✅ | ✅ | GPU workers |

## 🎉 **Success Indicators**

After successful deployment, you should see:

```bash
# All nodes ready
kubectl get nodes
# NAME     STATUS   ROLES           AGE   VERSION
# master   Ready    control-plane   5m    v1.28.0
# worker1  Ready    <none>          3m    v1.28.0
# worker2  Ready    <none>          3m    v1.28.0

# GPU resources available
kubectl describe nodes | grep -A 5 "Allocated resources"
# Allocated resources:
#   nvidia.com/gpu: 0

# ImagePod services running
kubectl get pods -n imagepod
# NAME                           READY   STATUS    RESTARTS   AGE
# imagepod-api-xxx               1/1     Running   0          2m
# postgres-0                     1/1     Running   0          3m
# redis-xxx                      1/1     Running   0          3m
# imagepod-gpu-worker-xxx        1/1     Running   0          2m
```

Your ImagePod infrastructure is now running on Kubernetes with proper node separation! 🎉
