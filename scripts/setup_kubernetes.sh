#!/bin/bash

# Kubernetes Setup Script for ImagePod GPU Workers
# This script sets up Kubernetes with GPU support on Ubuntu/Debian

set -e

echo "🚀 Setting up Kubernetes with GPU support for ImagePod..."

# Configuration
KUBERNETES_VERSION="1.28"
CONTAINERD_VERSION="1.7.6"
NVIDIA_DRIVER_VERSION="535"
NVIDIA_CONTAINER_TOOLKIT_VERSION="1.13.5"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as a regular user with sudo privileges."
   exit 1
fi

# Check if sudo is available
if ! command -v sudo &> /dev/null; then
    print_error "sudo is not available. Please install sudo or run as root."
    exit 1
fi

print_status "Starting Kubernetes setup..."

# Update system packages
print_status "Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# Install required packages
print_status "Installing required packages..."
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    wget \
    git \
    vim \
    htop \
    net-tools

# Install Docker
print_status "Installing Docker..."
if ! command -v docker &> /dev/null; then
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
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    print_success "Docker installed successfully"
else
    print_warning "Docker is already installed"
fi

# Install NVIDIA drivers
print_status "Installing NVIDIA drivers..."
if ! command -v nvidia-smi &> /dev/null; then
    # Add NVIDIA repository
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.0-1_all.deb
    sudo dpkg -i cuda-keyring_1.0-1_all.deb
    sudo apt-get update
    
    # Install NVIDIA drivers
    sudo apt-get install -y nvidia-driver-${NVIDIA_DRIVER_VERSION}
    
    print_success "NVIDIA drivers installed. Please reboot your system."
    print_warning "After reboot, run: nvidia-smi to verify GPU detection"
else
    print_success "NVIDIA drivers are already installed"
fi

# Install NVIDIA Container Toolkit
print_status "Installing NVIDIA Container Toolkit..."
if ! command -v nvidia-ctk &> /dev/null; then
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
    
    print_success "NVIDIA Container Toolkit installed successfully"
else
    print_success "NVIDIA Container Toolkit is already installed"
fi

# Install kubectl
print_status "Installing kubectl..."
if ! command -v kubectl &> /dev/null; then
    # Download kubectl
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    rm kubectl
    
    print_success "kubectl installed successfully"
else
    print_success "kubectl is already installed"
fi

# Install kubeadm, kubelet, and kubectl
print_status "Installing Kubernetes components..."
if ! command -v kubeadm &> /dev/null; then
    # Add Kubernetes repository
    curl -fsSL https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
    echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
    
    # Install Kubernetes components
    sudo apt-get update
    sudo apt-get install -y kubelet kubeadm kubectl
    sudo apt-mark hold kubelet kubeadm kubectl
    
    print_success "Kubernetes components installed successfully"
else
    print_success "Kubernetes components are already installed"
fi

# Configure system for Kubernetes
print_status "Configuring system for Kubernetes..."

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

# Configure containerd
print_status "Configuring containerd..."
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

# Initialize Kubernetes cluster
print_status "Initializing Kubernetes cluster..."
if ! kubectl cluster-info &> /dev/null; then
    # Initialize cluster
    sudo kubeadm init \
        --pod-network-cidr=10.244.0.0/16 \
        --cri-socket=unix:///var/run/containerd/containerd.sock \
        --kubernetes-version=v${KUBERNETES_VERSION}
    
    # Configure kubectl for current user
    mkdir -p $HOME/.kube
    sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
    sudo chown $(id -u):$(id -g) $HOME/.kube/config
    
    print_success "Kubernetes cluster initialized successfully"
else
    print_success "Kubernetes cluster is already initialized"
fi

# Install Flannel CNI
print_status "Installing Flannel CNI..."
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml

# Wait for nodes to be ready
print_status "Waiting for nodes to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s

# Label node for GPU workloads
print_status "Labeling node for GPU workloads..."
NODE_NAME=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
kubectl label node $NODE_NAME accelerator=nvidia-tesla-gpu

# Install NVIDIA Device Plugin
print_status "Installing NVIDIA Device Plugin..."
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml

# Wait for device plugin to be ready
print_status "Waiting for NVIDIA Device Plugin to be ready..."
kubectl wait --for=condition=Ready pod -l name=nvidia-device-plugin-ds -n kube-system --timeout=300s

# Create ImagePod namespace
print_status "Creating ImagePod namespace..."
kubectl create namespace imagepod --dry-run=client -o yaml | kubectl apply -f -

# Verify installation
print_status "Verifying installation..."
echo ""
echo "=== Kubernetes Cluster Status ==="
kubectl get nodes
echo ""
echo "=== GPU Resources ==="
kubectl describe nodes | grep -A 5 "Allocated resources"
echo ""
echo "=== NVIDIA Device Plugin Status ==="
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds

# Create deployment script
print_status "Creating deployment script..."
cat > deploy_imagepod_gpu_workers.sh << 'EOF'
#!/bin/bash

# Deploy ImagePod GPU Workers to Kubernetes
set -e

echo "🚀 Deploying ImagePod GPU Workers..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to Kubernetes
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster"
    exit 1
fi

# Create namespace if it doesn't exist
kubectl create namespace imagepod --dry-run=client -o yaml | kubectl apply -f -

# Create secrets
kubectl create secret generic imagepod-secrets \
    --from-literal=registration-token="your-registration-token-here" \
    --from-literal=api-key="your-api-key-here" \
    --namespace=imagepod \
    --dry-run=client -o yaml | kubectl apply -f -

# Deploy GPU worker DaemonSet
kubectl apply -f k8s/gpu-worker-daemonset.yaml

# Deploy GPU worker services
kubectl apply -f k8s/gpu-worker-service.yaml

# Wait for pods to be ready
kubectl wait --for=condition=Ready pod -l app=imagepod-gpu-worker -n imagepod --timeout=300s

echo "✅ ImagePod GPU Workers deployed successfully!"
echo ""
echo "🔍 To check the status:"
echo "  kubectl get pods -n imagepod -l app=imagepod-gpu-worker"
echo "  kubectl logs -n imagepod -l app=imagepod-gpu-worker"
EOF

chmod +x deploy_imagepod_gpu_workers.sh

print_success "Kubernetes setup completed successfully!"
echo ""
echo "🎉 Next steps:"
echo "1. Reboot your system to ensure NVIDIA drivers are loaded properly"
echo "2. After reboot, run: nvidia-smi to verify GPU detection"
echo "3. Run: ./deploy_imagepod_gpu_workers.sh to deploy ImagePod GPU workers"
echo ""
echo "🔍 Useful commands:"
echo "  kubectl get nodes                    # Check cluster status"
echo "  kubectl get pods -A                  # Check all pods"
echo "  kubectl describe nodes               # Check GPU resources"
echo "  nvidia-smi                          # Check GPU status"
echo ""
echo "📚 Documentation:"
echo "  https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/"
echo "  https://docs.nvidia.com/datacenter/cloud-native/kubernetes/install-k8s.html"
