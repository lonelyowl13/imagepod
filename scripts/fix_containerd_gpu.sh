#!/bin/bash

# Fix containerd configuration for GPU worker nodes
# This script fixes the containerd configuration issue

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

print_status "Fixing containerd configuration for GPU worker..."

# Stop containerd service
print_status "Stopping containerd service..."
sudo systemctl stop containerd

# Backup existing config
if [ -f /etc/containerd/config.toml ]; then
    print_status "Backing up existing containerd config..."
    sudo cp /etc/containerd/config.toml /etc/containerd/config.toml.backup
fi

# Create correct containerd configuration
print_status "Creating correct containerd configuration..."
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

# Restart containerd
print_status "Restarting containerd service..."
sudo systemctl start containerd
sudo systemctl enable containerd

# Wait a moment for containerd to start
sleep 3

# Check containerd status
print_status "Checking containerd status..."
if sudo systemctl is-active --quiet containerd; then
    print_success "containerd is now running successfully!"
else
    print_error "containerd is still not running. Let's check the logs..."
    sudo journalctl -u containerd --no-pager -l
    exit 1
fi

# Verify containerd is working
print_status "Verifying containerd is working..."
if sudo ctr version &> /dev/null; then
    print_success "containerd is working correctly!"
else
    print_warning "containerd might have issues. Let's check the logs..."
    sudo journalctl -u containerd --no-pager -l
fi

print_success "containerd configuration fixed!"
echo ""
echo "🎉 containerd is now working correctly!"
echo ""
echo "🔍 To verify:"
echo "  sudo systemctl status containerd"
echo "  sudo ctr version"
echo ""
echo "📊 To check logs if needed:"
echo "  sudo journalctl -u containerd -f"
