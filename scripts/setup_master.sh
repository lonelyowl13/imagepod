#!/bin/bash

# ImagePod Master Node Setup Script
# This script sets up a Kubernetes master node and deploys ImagePod services

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

print_status "🚀 Setting up ImagePod Master Node..."
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
    cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
br_netfilter
EOF
    
    # Load modules
    sudo modprobe br_netfilter
    
    # Configure sysctl
    cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
    
    sudo sysctl --system
    
    print_success "System configured for Kubernetes"
}

# Function to initialize Kubernetes cluster
init_cluster() {
    print_status "Initializing Kubernetes cluster..."
    
    # Get the primary network interface IP
    MASTER_IP=$(ip route get 8.8.8.8 | awk '{print $7; exit}')
    
    print_status "Using master IP: $MASTER_IP"
    
    # Initialize cluster
    sudo kubeadm init \
        --pod-network-cidr=10.244.0.0/16 \
        --apiserver-advertise-address=$MASTER_IP \
        --control-plane-endpoint=$MASTER_IP
    
    # Configure kubectl for current user
    mkdir -p $HOME/.kube
    sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
    sudo chown $(id -u):$(id -g) $HOME/.kube/config
    
    print_success "Kubernetes cluster initialized"
    
    # Save join command
    sudo kubeadm token create --print-join-command > /tmp/kubeadm-join-command.txt
    print_success "Join command saved to /tmp/kubeadm-join-command.txt"
    print_warning "Save this join command for your worker nodes!"
    cat /tmp/kubeadm-join-command.txt
}

# Function to install CNI plugin (Flannel)
install_cni() {
    print_status "Installing CNI plugin (Flannel)..."
    
    kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
    
    # Wait for pods to be ready
    print_status "Waiting for CNI pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=flannel -n kube-flannel --timeout=300s
    
    print_success "CNI plugin installed"
}

# Function to deploy ImagePod services
deploy_imagepod() {
    print_status "Deploying ImagePod services..."
    
    # Generate secrets if they don't exist
    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
        print_status "Generating secrets..."
        "$SCRIPT_DIR/generate_secrets.sh"
    fi
    
    # Deploy ImagePod services
    "$SCRIPT_DIR/deploy_full_kubernetes.sh"
    
    print_success "ImagePod services deployed"
}

# Function to show status
show_status() {
    print_status "Checking cluster status..."
    
    echo ""
    echo "🔍 Cluster Status:"
    kubectl get nodes
    
    echo ""
    echo "🔍 ImagePod Services:"
    kubectl get pods -n imagepod
    
    echo ""
    echo "🔍 All Services:"
    kubectl get services -n imagepod
    
    echo ""
    print_success "Master node setup completed!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Copy the join command from /tmp/kubeadm-join-command.txt"
    echo "2. Run it on your GPU worker nodes"
    echo "3. Check cluster status with: kubectl get nodes"
    echo ""
    echo "🌐 Access ImagePod API:"
    echo "  kubectl port-forward -n imagepod svc/imagepod-api 8000:8000"
    echo "  Then visit: http://localhost:8000"
}

# Main execution
main() {
    print_status "Starting ImagePod Master Node setup..."
    
    install_packages
    install_docker
    install_kubernetes
    configure_system
    init_cluster
    install_cni
    deploy_imagepod
    show_status
}

# Run main function
main "$@"
