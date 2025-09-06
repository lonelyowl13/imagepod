#!/bin/bash

# Final Fix for Kubernetes Repository Script
# This script fixes the broken Kubernetes repository configuration

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

print_status "Fixing Kubernetes repository configuration..."

# Remove ALL broken repository configurations
print_status "Removing broken repository configurations..."
sudo rm -f /etc/apt/sources.list.d/kubernetes.list
sudo rm -f /etc/apt/keyrings/kubernetes-apt-keyring.gpg
sudo rm -f /usr/share/keyrings/kubernetes-archive-keyring.gpg

# Clean apt cache
print_status "Cleaning apt cache..."
sudo apt-get clean
sudo apt-get autoclean

# Add the NEW working Kubernetes repository
print_status "Adding the new working Kubernetes repository..."
KUBERNETES_VERSION="1.28"

# Create the keyring directory if it doesn't exist
sudo mkdir -p /etc/apt/keyrings

# Add the new repository key and source
curl -fsSL https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_VERSION}/deb/ /" | sudo tee /etc/apt/sources.list.d/kubernetes.list

# Update package lists
print_status "Updating package lists..."
sudo apt-get update

print_success "Kubernetes repository fixed successfully!"
echo ""
echo "🎉 You can now continue with the Kubernetes installation:"
echo "  sudo apt-get install -y kubelet kubeadm kubectl"
echo "  sudo apt-mark hold kubelet kubeadm kubectl"
echo ""
echo "📋 Or run the full setup:"
echo "  ./scripts/setup_kubernetes_master_fixed.sh"
