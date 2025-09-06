#!/bin/bash

# Fix Kubernetes Repository Script
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

# Remove broken repository configuration
print_status "Removing broken repository configuration..."
sudo rm -f /etc/apt/sources.list.d/kubernetes.list
sudo rm -f /etc/apt/keyrings/kubernetes-apt-keyring.gpg

# Add correct Kubernetes repository
print_status "Adding correct Kubernetes repository..."
curl -sS https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/kubernetes-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list

# Update package lists
print_status "Updating package lists..."
sudo apt-get update

print_success "Kubernetes repository fixed successfully!"
echo ""
echo "🎉 You can now continue with the Kubernetes installation:"
echo "  sudo apt-get install -y kubelet kubeadm kubectl"
echo "  sudo apt-mark hold kubelet kubeadm kubectl"
