#!/bin/bash

# ImagePod Kubernetes Master Node Setup Script (FIXED)
# This script sets up Kubernetes master node WITHOUT GPU support

set -e

# Configuration
KUBERNETES_VERSION="1.28"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_status "Starting Kubernetes Master Node setup (NO GPU)..."
echo ""

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
    # Remove any existing broken repository
    sudo rm -f /etc/apt/sources.list.d/kubernetes.list
    sudo rm -f /etc/apt/keyrings/kubernetes-apt-keyring.gpg
    sudo rm -f /usr/share/keyrings/kubernetes-archive-keyring.gpg
    
    # Add the NEW working Kubernetes repository
    curl -fsSL https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
    echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/ /" | sudo tee /etc/apt/sources.list.d/kubernetes.list
    
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

# Configure containerd (NO NVIDIA support)
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
        --kubernetes-version=v${KUBERNETES_VERSION}.0
    
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

# Remove taint from master node to allow scheduling
print_status "Removing taint from master node..."
kubectl taint nodes --all node-role.kubernetes.io/control-plane-

# Create ImagePod namespace
print_status "Creating ImagePod namespace..."
kubectl create namespace imagepod --dry-run=client -o yaml | kubectl apply -f -

# Verify installation
print_status "Verifying installation..."
echo ""
echo "=== Kubernetes Cluster Status ==="
kubectl get nodes
echo ""
echo "=== Pods in kube-system ==="
kubectl get pods -n kube-system

print_success "Kubernetes Master Node setup completed!"
echo ""
echo "🎉 Next steps:"
echo "1. Note the kubeadm join command from the output above"
echo "2. Run the join command on worker nodes"
echo "3. Deploy ImagePod: ./scripts/deploy_full_kubernetes.sh"
echo ""
echo "🔍 To check the status:"
echo "  kubectl get nodes"
echo "  kubectl get pods -A"
echo ""
echo "📊 To monitor the cluster:"
echo "  kubectl top nodes"
echo "  kubectl describe nodes"
echo ""
echo "🚀 To deploy ImagePod:"
echo "  ./scripts/deploy_full_kubernetes.sh"
