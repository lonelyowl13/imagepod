#!/bin/bash

# ImagePod Shutdown Script
# This script shuts down all ImagePod services and cleans up the system

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

print_status "🛑 Shutting down ImagePod services..."

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root. Please run as a regular user with sudo access."
        exit 1
    fi
}

# Function to stop Kubernetes services
stop_kubernetes() {
    print_status "Stopping Kubernetes services..."
    
    if command -v kubectl &> /dev/null; then
        # Check if we're connected to a cluster
        if kubectl cluster-info &> /dev/null; then
            print_status "Stopping ImagePod pods..."
            kubectl delete namespace imagepod --ignore-not-found=true
            
            print_status "Stopping GPU worker pods..."
            kubectl delete daemonset gpu-worker-daemonset -n imagepod --ignore-not-found=true
            kubectl delete service gpu-worker-service -n imagepod --ignore-not-found=true
            
            print_success "Kubernetes services stopped"
        else
            print_warning "Not connected to a Kubernetes cluster"
        fi
    else
        print_warning "kubectl not found, skipping Kubernetes cleanup"
    fi
}

# Function to stop Docker services
stop_docker() {
    print_status "Stopping Docker services..."
    
    if command -v docker &> /dev/null; then
        # Stop all running containers
        print_status "Stopping all running containers..."
        docker stop $(docker ps -q) 2>/dev/null || true
        
        # Remove all containers
        print_status "Removing all containers..."
        docker rm $(docker ps -aq) 2>/dev/null || true
        
        # Stop Docker service
        print_status "Stopping Docker service..."
        sudo systemctl stop docker
        
        print_success "Docker services stopped"
    else
        print_warning "Docker not found, skipping Docker cleanup"
    fi
}

# Function to stop systemd services
stop_systemd_services() {
    print_status "Stopping systemd services..."
    
    # Stop ImagePod services
    sudo systemctl stop imagepod-api 2>/dev/null || true
    sudo systemctl stop imagepod-postgres 2>/dev/null || true
    sudo systemctl stop imagepod-redis 2>/dev/null || true
    sudo systemctl stop imagepod-gpu-worker 2>/dev/null || true
    
    # Stop Kubernetes services
    sudo systemctl stop kubelet 2>/dev/null || true
    sudo systemctl stop containerd 2>/dev/null || true
    
    print_success "Systemd services stopped"
}

# Function to clean up Kubernetes
cleanup_kubernetes() {
    print_status "Cleaning up Kubernetes..."
    
    if command -v kubeadm &> /dev/null; then
        # Reset kubeadm if this is a master node
        if [[ -f /etc/kubernetes/admin.conf ]]; then
            print_warning "This appears to be a master node. Resetting kubeadm..."
            sudo kubeadm reset --force
        fi
    fi
    
    # Clean up kubelet
    if command -v kubelet &> /dev/null; then
        print_status "Cleaning up kubelet..."
        sudo systemctl stop kubelet
        sudo systemctl disable kubelet
    fi
    
    # Clean up containerd
    if command -v containerd &> /dev/null; then
        print_status "Cleaning up containerd..."
        sudo systemctl stop containerd
        sudo systemctl disable containerd
    fi
    
    print_success "Kubernetes cleanup completed"
}

# Function to clean up Docker
cleanup_docker() {
    print_status "Cleaning up Docker..."
    
    if command -v docker &> /dev/null; then
        # Remove all images
        print_status "Removing all Docker images..."
        docker rmi $(docker images -q) 2>/dev/null || true
        
        # Remove all volumes
        print_status "Removing all Docker volumes..."
        docker volume rm $(docker volume ls -q) 2>/dev/null || true
        
        # Remove all networks
        print_status "Removing all Docker networks..."
        docker network rm $(docker network ls -q) 2>/dev/null || true
        
        # Stop and disable Docker service
        sudo systemctl stop docker
        sudo systemctl disable docker
        
        print_success "Docker cleanup completed"
    fi
}

# Function to clean up files
cleanup_files() {
    print_status "Cleaning up files..."
    
    # Remove ImagePod directories
    sudo rm -rf /opt/imagepod 2>/dev/null || true
    sudo rm -rf /opt/imagepod-gpu-worker 2>/dev/null || true
    
    # Remove Kubernetes configuration
    sudo rm -rf /etc/kubernetes 2>/dev/null || true
    sudo rm -rf /var/lib/kubelet 2>/dev/null || true
    sudo rm -rf /var/lib/etcd 2>/dev/null || true
    sudo rm -rf /var/lib/containerd 2>/dev/null || true
    
    # Remove Docker data
    sudo rm -rf /var/lib/docker 2>/dev/null || true
    
    # Remove kubectl config
    rm -rf ~/.kube 2>/dev/null || true
    
    # Remove temporary files
    rm -f /tmp/kubeadm-join-command.txt 2>/dev/null || true
    
    print_success "Files cleanup completed"
}

# Function to clean up network configuration
cleanup_network() {
    print_status "Cleaning up network configuration..."
    
    # Remove iptables rules
    sudo iptables -F 2>/dev/null || true
    sudo iptables -t nat -F 2>/dev/null || true
    sudo iptables -t mangle -F 2>/dev/null || true
    sudo iptables -X 2>/dev/null || true
    
    # Remove sysctl configuration
    sudo rm -f /etc/sysctl.d/k8s.conf 2>/dev/null || true
    sudo rm -f /etc/modules-load.d/k8s.conf 2>/dev/null || true
    
    # Restore swap
    sudo sed -i '/ swap / s/^#\(.*\)$/\1/g' /etc/fstab 2>/dev/null || true
    
    print_success "Network configuration cleanup completed"
}

# Function to uninstall packages
uninstall_packages() {
    print_status "Uninstalling packages..."
    
    # Detect OS
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
    else
        print_error "Cannot detect OS version"
        exit 1
    fi
    
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        # Uninstall Kubernetes packages
        sudo apt-get remove -y kubelet kubeadm kubectl 2>/dev/null || true
        
        # Uninstall Docker
        sudo apt-get remove -y docker-ce docker-ce-cli containerd.io docker-compose-plugin 2>/dev/null || true
        
        # Uninstall NVIDIA packages
        sudo apt-get remove -y nvidia-docker2 2>/dev/null || true
        
        # Clean up
        sudo apt-get autoremove -y
        sudo apt-get autoclean
        
    elif [[ "$OS" == "arch" ]]; then
        # Uninstall Kubernetes packages
        sudo pacman -R --noconfirm kubectl kubeadm kubelet 2>/dev/null || true
        
        # Uninstall Docker
        sudo pacman -R --noconfirm docker docker-compose 2>/dev/null || true
        
        # Uninstall NVIDIA packages
        sudo pacman -R --noconfirm nvidia-container-toolkit 2>/dev/null || true
    fi
    
    print_success "Packages uninstalled"
}

# Function to show cleanup summary
show_summary() {
    print_status "Cleanup summary:"
    echo ""
    echo "✅ Stopped all ImagePod services"
    echo "✅ Stopped Kubernetes cluster"
    echo "✅ Stopped Docker services"
    echo "✅ Cleaned up all files and data"
    echo "✅ Cleaned up network configuration"
    echo "✅ Uninstalled packages"
    echo ""
    print_success "ImagePod shutdown completed!"
    echo ""
    echo "🔄 To restart ImagePod:"
    echo "  ./scripts/setup_master.sh    # On master node"
    echo "  ./scripts/setup_worker.sh    # On worker nodes"
    echo ""
    echo "⚠️  Note: All data has been removed. You'll need to reconfigure everything."
}

# Function to confirm shutdown
confirm_shutdown() {
    echo ""
    print_warning "This will completely shut down and remove all ImagePod services and data."
    print_warning "This action cannot be undone!"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        print_status "Shutdown cancelled."
        exit 0
    fi
}

# Main execution
main() {
    print_status "Starting ImagePod shutdown process..."
    
    check_root
    confirm_shutdown
    
    stop_kubernetes
    stop_docker
    stop_systemd_services
    cleanup_kubernetes
    cleanup_docker
    cleanup_files
    cleanup_network
    uninstall_packages
    show_summary
}

# Run main function
main "$@"
