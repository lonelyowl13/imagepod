#!/bin/bash

# ImagePod GPU Worker Setup Script (Simple Docker-based)
# This script sets up a GPU worker on a GPU server without Kubernetes

set -e

echo "🚀 Setting up ImagePod GPU Worker (Simple Docker-based)..."

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

# Configuration
API_ENDPOINT="${API_ENDPOINT:-http://localhost:8000}"
REGISTRATION_TOKEN="${REGISTRATION_TOKEN:-your-registration-token-here}"
WORKER_PORT="${WORKER_PORT:-8080}"

print_status "Starting GPU Worker setup..."

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
    net-tools \
    python3 \
    python3-pip \
    python3-venv \
    docker.io \
    docker-compose

# Install Docker (if not already installed)
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
    sudo apt-get install -y nvidia-driver-535
    
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
    
    # Configure Docker to use NVIDIA runtime
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
    
    print_success "NVIDIA Container Toolkit installed successfully"
else
    print_success "NVIDIA Container Toolkit is already installed"
fi

# Create ImagePod GPU Worker directory
print_status "Setting up ImagePod GPU Worker directory..."
if [ ! -d "/opt/imagepod-gpu-worker" ]; then
    sudo mkdir -p /opt/imagepod-gpu-worker
    sudo chown $USER:$USER /opt/imagepod-gpu-worker
fi

# Copy worker agent files
print_status "Copying worker agent files..."
# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cp -r "$PROJECT_DIR/worker_agent"/* /opt/imagepod-gpu-worker/
cd /opt/imagepod-gpu-worker

# Create environment file
print_status "Creating environment configuration..."
cat > .env <<EOF
# ImagePod GPU Worker Configuration
API_ENDPOINT=${API_ENDPOINT}
REGISTRATION_TOKEN=${REGISTRATION_TOKEN}
NODE_NAME=$(hostname)
POD_NAME=simple-gpu-worker
LOG_LEVEL=INFO
HEARTBEAT_INTERVAL=30
MAX_CONCURRENT_JOBS=1
WORKER_PORT=${WORKER_PORT}
EOF

# Create Docker Compose file for GPU worker
print_status "Creating Docker Compose configuration..."
cat > docker-compose.yml <<EOF
version: '3.8'

services:
  gpu-worker:
    build: .
    container_name: imagepod-gpu-worker
    restart: unless-stopped
    ports:
      - "${WORKER_PORT}:8080"
      - "8081:8081"
    environment:
      - API_ENDPOINT=${API_ENDPOINT}
      - REGISTRATION_TOKEN=${REGISTRATION_TOKEN}
      - NODE_NAME=$(hostname)
      - POD_NAME=simple-gpu-worker
      - LOG_LEVEL=INFO
      - HEARTBEAT_INTERVAL=30
      - MAX_CONCURRENT_JOBS=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp/imagepod:/tmp/imagepod
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
EOF

# Create systemd service for GPU worker
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/imagepod-gpu-worker.service <<EOF
[Unit]
Description=ImagePod GPU Worker Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/imagepod-gpu-worker
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0
User=$USER
Group=$USER
Environment="NVIDIA_VISIBLE_DEVICES=all"
Environment="NVIDIA_DRIVER_CAPABILITIES=compute,utility"

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
sudo systemctl daemon-reload
sudo systemctl enable imagepod-gpu-worker.service

print_success "ImagePod GPU Worker setup completed!"
echo ""
echo "🎉 Next steps:"
echo "1. Edit configuration: nano /opt/imagepod-gpu-worker/.env"
echo "2. Set your API_ENDPOINT and REGISTRATION_TOKEN"
echo "3. Reboot if NVIDIA drivers were installed"
echo "4. Start the service: sudo systemctl start imagepod-gpu-worker"
echo "5. Check status: sudo systemctl status imagepod-gpu-worker"
echo ""
echo "🔍 Useful commands:"
echo "  sudo systemctl start imagepod-gpu-worker     # Start GPU Worker"
echo "  sudo systemctl stop imagepod-gpu-worker      # Stop GPU Worker"
echo "  sudo systemctl restart imagepod-gpu-worker   # Restart GPU Worker"
echo "  sudo systemctl status imagepod-gpu-worker    # Check status"
echo "  docker-compose logs -f                       # View logs"
echo ""
echo "🌐 Access GPU Worker:"
echo "  Health: http://localhost:${WORKER_PORT}/health"
echo "  Status: http://localhost:${WORKER_PORT}/status"
echo ""
echo "📊 Monitor GPU:"
echo "  nvidia-smi                                  # Check GPU status"
echo "  docker stats                                # Check container stats"
