#!/bin/bash

# ImagePod Kubernetes Master Node Setup Script for Arch Linux
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

print_status "Starting Kubernetes Master Node setup for Arch Linux (NO GPU)..."
echo ""

# Update system packages
print_status "Updating system packages..."
sudo pacman -Syu --noconfirm

# Install required packages
print_status "Installing required packages..."
sudo pacman -S --noconfirm \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    iptables \
    iproute2

# Install Docker
print_status "Installing Docker..."
if ! command -v docker &> /dev/null; then
    sudo pacman -S --noconfirm docker docker-compose
    
    # Enable and start Docker
    sudo systemctl enable docker
    sudo systemctl start docker
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    print_success "Docker installed successfully"
    print_warning "Please log out and back in for docker group changes to take effect"
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

# Install kubeadm and kubelet
print_status "Installing Kubernetes components..."
if ! command -v kubeadm &> /dev/null; then
    # Download kubeadm and kubelet
    curl -LO "https://dl.k8s.io/release/v${KUBERNETES_VERSION}.0/bin/linux/amd64/kubeadm"
    curl -LO "https://dl.k8s.io/release/v${KUBERNETES_VERSION}.0/bin/linux/amd64/kubelet"
    
    sudo install -o root -g root -m 0755 kubeadm /usr/local/bin/kubeadm
    sudo install -o root -g root -m 0755 kubelet /usr/local/bin/kubelet
    
    rm kubeadm kubelet
    
    print_success "Kubernetes components installed successfully"
else
    print_success "Kubernetes components are already installed"
fi

# Install containerd
print_status "Installing containerd..."
if ! command -v containerd &> /dev/null; then
    sudo pacman -S --noconfirm containerd
    
    # Enable and start containerd
    sudo systemctl enable containerd
    sudo systemctl start containerd
    
    print_success "containerd installed successfully"
else
    print_warning "containerd is already installed"
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
