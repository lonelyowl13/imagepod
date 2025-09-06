#!/bin/bash

# ImagePod Kubernetes Worker Node Setup Script (FIXED)
# This script sets up Kubernetes worker node WITH GPU support

set -e

# Configuration
KUBERNETES_VERSION="1.28"
NVIDIA_DRIVER_VERSION="535"
NVIDIA_CONTAINER_TOOLKIT_VERSION="1.13.5"

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

print_status "Starting Kubernetes Worker Node setup (WITH GPU)..."
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

# Configure containerd (WITH NVIDIA support) - FIXED VERSION
print_status "Configuring containerd with NVIDIA support..."
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

# Configure NVIDIA Container Toolkit
print_status "Configuring NVIDIA Container Toolkit..."
sudo nvidia-ctk runtime configure --runtime=containerd

# Restart containerd
print_status "Restarting containerd service..."
sudo systemctl restart containerd
sudo systemctl enable containerd

# Wait for containerd to start
sleep 3

# Verify containerd is working
print_status "Verifying containerd is working..."
if sudo systemctl is-active --quiet containerd; then
    print_success "containerd is running successfully!"
else
    print_error "containerd failed to start. Let's check the logs..."
    sudo journalctl -u containerd --no-pager -l
    exit 1
fi

print_success "Kubernetes Worker Node setup completed!"
echo ""
echo "🎉 Next steps:"
echo "1. Reboot your system to load NVIDIA drivers"
echo "2. After reboot, run the kubeadm join command from the master node"
echo "3. Label this node for GPU workloads: kubectl label node <node-name> accelerator=nvidia-tesla-gpu"
echo ""
echo "🔍 To verify GPU after reboot:"
echo "  nvidia-smi"
echo "  kubectl describe nodes | grep -A 5 'Allocated resources'"
echo ""
echo "📊 To check node status:"
echo "  kubectl get nodes"
echo "  kubectl describe nodes"
