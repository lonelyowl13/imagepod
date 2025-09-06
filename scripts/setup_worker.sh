#!/bin/bash

# ImagePod GPU Worker Node Setup Script
# This script sets up a GPU worker node and joins it to the Kubernetes cluster

set -e

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

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

print_status "🚀 Setting up ImagePod GPU Worker Node..."
print_status "Project directory: $PROJECT_DIR"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as a regular user with sudo access."
   exit 1
fi

# Detect OS
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    print_error "Cannot detect OS version"
    exit 1
fi

print_status "Detected OS: $OS $VERSION"

# Function to install packages based on OS
install_packages() {
    print_status "Installing required packages..."
    
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        sudo apt-get update
        sudo apt-get install -y \
            apt-transport-https \
            ca-certificates \
            curl \
            gnupg \
            lsb-release \
            conntrack \
            ethtool \
            iptables \
            socat \
            jq
    elif [[ "$OS" == "arch" ]]; then
        sudo pacman -Sy --noconfirm \
            curl \
            wget \
            conntrack-tools \
            ethtool \
            iptables-nft \
            socat \
            jq
    else
        print_error "Unsupported OS: $OS"
        exit 1
    fi
}

# Function to install NVIDIA drivers
install_nvidia_drivers() {
    print_status "Installing NVIDIA drivers..."
    
    if command -v nvidia-smi &> /dev/null; then
        print_warning "NVIDIA drivers already installed"
        nvidia-smi
        return
    fi
    
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        # Add NVIDIA repository
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
        
        sudo apt-get update
        sudo apt-get install -y nvidia-driver-535 nvidia-docker2
    elif [[ "$OS" == "arch" ]]; then
        sudo pacman -S --noconfirm nvidia nvidia-utils nvidia-settings
    fi
    
    print_success "NVIDIA drivers installed. Please reboot and run this script again."
    exit 0
}

# Function to install Docker
install_docker() {
    print_status "Installing Docker..."
    
    if command -v docker &> /dev/null; then
        print_warning "Docker already installed"
        return
    fi
    
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        # Add Docker's official GPG key
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        
        # Add Docker repository
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    elif [[ "$OS" == "arch" ]]; then
        sudo pacman -S --noconfirm docker docker-compose
    fi
    
    # Start and enable Docker
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    
    print_success "Docker installed successfully"
}

# Function to install Kubernetes
install_kubernetes() {
    print_status "Installing Kubernetes..."
    
    if command -v kubectl &> /dev/null; then
        print_warning "Kubernetes already installed"
        return
    fi
    
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        # Add Kubernetes GPG key
        curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/kubernetes-archive-keyring.gpg
        
        # Add Kubernetes repository
        echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list
        
        sudo apt-get update
        sudo apt-get install -y kubelet kubeadm kubectl
    elif [[ "$OS" == "arch" ]]; then
        sudo pacman -S --noconfirm kubectl kubeadm kubelet
    fi
    
    # Hold packages at current version
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        sudo apt-mark hold kubelet kubeadm kubectl
    fi
    
    print_success "Kubernetes installed successfully"
}

# Function to configure system for Kubernetes
configure_system() {
    print_status "Configuring system for Kubernetes..."
    
    # Disable swap
    sudo swapoff -a
    sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
    
    # Load required kernel modules
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
br_netfilter
overlay
EOF
    elif [[ "$OS" == "arch" ]]; then
        # On Arch, overlay is built into kernel, so only load br_netfilter
        cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
br_netfilter
EOF
    fi
    
    # Load modules
    sudo modprobe br_netfilter
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        sudo modprobe overlay
    fi
    
    # Configure sysctl
    cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
    
    sudo sysctl --system
    
    print_success "System configured for Kubernetes"
}

# Function to configure containerd for GPU support
configure_containerd() {
    print_status "Configuring containerd for GPU support..."
    
    # Create containerd config directory
    sudo mkdir -p /etc/containerd
    
    # Generate containerd config
    sudo containerd config default | sudo tee /etc/containerd/config.toml
    
    # Configure NVIDIA runtime
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
        sudo sed -i 's/runtime = "runc"/runtime = "nvidia"/' /etc/containerd/config.toml
        
        # Add NVIDIA runtime configuration
        sudo tee -a /etc/containerd/config.toml > /dev/null <<EOF

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
  runtime_type = "io.containerd.runc.v2"
  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
    BinaryName = "nvidia-container-runtime"
EOF
    elif [[ "$OS" == "arch" ]]; then
        sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
        sudo sed -i 's/runtime = "runc"/runtime = "nvidia"/' /etc/containerd/config.toml
        
        # Add NVIDIA runtime configuration for Arch
        sudo tee -a /etc/containerd/config.toml > /dev/null <<EOF

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
  runtime_type = "io.containerd.runc.v2"
  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
    BinaryName = "nvidia-container-runtime"
EOF
    fi
    
    # Restart containerd
    sudo systemctl restart containerd
    sudo systemctl enable containerd
    
    print_success "Containerd configured for GPU support"
}

# Function to configure hostname resolution
configure_hostname() {
    print_status "Configuring hostname resolution..."
    
    HOSTNAME=$(hostname)
    if ! grep -q "$HOSTNAME" /etc/hosts; then
        echo "127.0.0.1 $HOSTNAME" | sudo tee -a /etc/hosts
        print_success "Added hostname to /etc/hosts"
    else
        print_warning "Hostname already in /etc/hosts"
    fi
}

# Function to join cluster
join_cluster() {
    print_status "Joining Kubernetes cluster..."
    
    if [[ -z "$1" ]]; then
        print_error "Please provide the kubeadm join command as an argument"
        print_error "Usage: $0 'kubeadm join <master-ip>:6443 --token <token> --discovery-token-ca-cert-hash <hash>'"
        exit 1
    fi
    
    JOIN_COMMAND="$1"
    
    print_status "Executing join command..."
    sudo $JOIN_COMMAND
    
    print_success "Successfully joined the cluster!"
}

# Function to deploy GPU worker agent
deploy_gpu_agent() {
    print_status "Deploying GPU worker agent..."
    
    # Wait for node to be ready
    print_status "Waiting for node to be ready..."
    sleep 30
    
    # Deploy GPU worker DaemonSet
    kubectl apply -f "$PROJECT_DIR/k8s/gpu-worker-daemonset.yaml"
    kubectl apply -f "$PROJECT_DIR/k8s/gpu-worker-service.yaml"
    
    print_success "GPU worker agent deployed"
}

# Function to show status
show_status() {
    print_status "Checking worker status..."
    
    echo ""
    echo "🔍 Node Status:"
    kubectl get nodes
    
    echo ""
    echo "🔍 GPU Worker Pods:"
    kubectl get pods -n imagepod -l app=gpu-worker
    
    echo ""
    echo "🔍 NVIDIA GPU Status:"
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi
    else
        print_warning "nvidia-smi not found"
    fi
    
    echo ""
    print_success "GPU worker node setup completed!"
    echo ""
    echo "📋 Your GPU worker is now ready to process ImagePod jobs!"
    echo ""
    echo "🔍 To check status:"
    echo "  kubectl get nodes"
    echo "  kubectl get pods -n imagepod"
    echo "  nvidia-smi"
}

# Main execution
main() {
    print_status "Starting ImagePod GPU Worker Node setup..."
    
    # Check if NVIDIA drivers are installed
    if ! command -v nvidia-smi &> /dev/null; then
        install_nvidia_drivers
        return
    fi
    
    install_packages
    install_docker
    install_kubernetes
    configure_system
    configure_containerd
    configure_hostname
    
    # Join cluster if command provided
    if [[ -n "$1" ]]; then
        join_cluster "$1"
        deploy_gpu_agent
        show_status
    else
        print_warning "No join command provided. Run with join command to complete setup:"
        print_warning "Usage: $0 'kubeadm join <master-ip>:6443 --token <token> --discovery-token-ca-cert-hash <hash>'"
    fi
}

# Run main function
main "$@"
