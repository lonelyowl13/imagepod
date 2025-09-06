#!/bin/bash

# ImagePod Kubernetes Worker Node Setup Script for Arch Linux
# This script sets up Kubernetes worker node WITH GPU support on Arch Linux

set -e

# Configuration
KUBERNETES_VERSION="1.28"
NVIDIA_DRIVER_VERSION="535"

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

print_status "Starting Kubernetes Worker Node setup for Arch Linux (WITH GPU)..."
echo ""

# Update system packages
print_status "Updating system packages..."
sudo pacman -Syu --noconfirm

# Install required packages
print_status "Installing required packages..."
sudo pacman -S --noconfirm \
    base-devel \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    openssh \
    rsync

# Install Docker
print_status "Installing Docker..."
if ! command -v docker &> /dev/null; then
    sudo pacman -S --noconfirm docker docker-compose
    sudo systemctl enable docker
    sudo systemctl start docker
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    print_success "Docker installed successfully"
else
    print_warning "Docker is already installed"
fi

# Install NVIDIA drivers
print_status "Installing NVIDIA drivers..."
if ! command -v nvidia-smi &> /dev/null; then
    # Install NVIDIA drivers
    sudo pacman -S --noconfirm nvidia nvidia-utils nvidia-settings
    
    print_success "NVIDIA drivers installed. Please reboot your system."
    print_warning "After reboot, run: nvidia-smi to verify GPU detection"
else
    print_success "NVIDIA drivers are already installed"
fi

# Install NVIDIA Container Toolkit
print_status "Installing NVIDIA Container Toolkit..."
if ! command -v nvidia-ctk &> /dev/null; then
    # Install NVIDIA Container Toolkit from AUR
    if command -v yay &> /dev/null; then
        yay -S --noconfirm nvidia-container-toolkit
    elif command -v paru &> /dev/null; then
        paru -S --noconfirm nvidia-container-toolkit
    else
        print_warning "No AUR helper found. Installing nvidia-container-toolkit manually..."
        # Install nvidia-container-toolkit manually
        cd /tmp
        git clone https://aur.archlinux.org/nvidia-container-toolkit.git
        cd nvidia-container-toolkit
        makepkg -si --noconfirm
        cd ~
    fi
    
    print_success "NVIDIA Container Toolkit installed successfully"
else
    print_success "NVIDIA Container Toolkit is already installed"
fi

# Install kubectl
print_status "Installing kubectl..."
if ! command -v kubectl &> /dev/null; then
    sudo pacman -S --noconfirm kubectl
    print_success "kubectl installed successfully"
else
    print_success "kubectl is already installed"
fi

# Install kubeadm and kubelet
print_status "Installing Kubernetes components..."
if ! command -v kubeadm &> /dev/null; then
    # Install kubeadm and kubelet from AUR
    if command -v yay &> /dev/null; then
        yay -S --noconfirm kubeadm kubelet
    elif command -v paru &> /dev/null; then
        paru -S --noconfirm kubeadm kubelet
    else
        print_warning "No AUR helper found. Installing kubeadm and kubelet manually..."
        # Install kubeadm and kubelet manually
        cd /tmp
        git clone https://aur.archlinux.org/kubeadm.git
        cd kubeadm
        makepkg -si --noconfirm
        cd ~
        
        cd /tmp
        git clone https://aur.archlinux.org/kubelet.git
        cd kubelet
        makepkg -si --noconfirm
        cd ~
    fi
    
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

print_success "Kubernetes Worker Node setup completed for Arch Linux!"
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
echo ""
echo "💡 Note: This script uses pacman and AUR helpers (yay/paru) for Arch Linux"
