#!/bin/bash

# ImagePod Backend Setup Script (No GPU Required)
# This script sets up the ImagePod backend service on a simple server

set -e

echo "🚀 Setting up ImagePod Backend Service..."

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

print_status "Starting ImagePod Backend setup..."

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

# Install Docker Compose (if not already installed)
print_status "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose installed successfully"
else
    print_warning "Docker Compose is already installed"
fi

# Create ImagePod directory
print_status "Setting up ImagePod directory..."
if [ ! -d "/opt/imagepod" ]; then
    sudo mkdir -p /opt/imagepod
    sudo chown $USER:$USER /opt/imagepod
fi

# Copy ImagePod files
print_status "Copying ImagePod files..."
# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cp -r "$PROJECT_DIR"/* /opt/imagepod/
cd /opt/imagepod

# Create environment file
print_status "Creating environment configuration..."
if [ ! -f ".env" ]; then
    cp env.example .env
    print_warning "Please edit .env file with your configuration"
fi

# Create systemd service for ImagePod
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/imagepod.service <<EOF
[Unit]
Description=ImagePod Backend Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/imagepod
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable imagepod.service

print_success "ImagePod Backend setup completed!"
echo ""
echo "🎉 Next steps:"
echo "1. Edit configuration: sudo nano /opt/imagepod/.env"
echo "2. Start the service: sudo systemctl start imagepod"
echo "3. Check status: sudo systemctl status imagepod"
echo "4. View logs: sudo journalctl -u imagepod -f"
echo ""
echo "🔍 Useful commands:"
echo "  sudo systemctl start imagepod     # Start ImagePod"
echo "  sudo systemctl stop imagepod      # Stop ImagePod"
echo "  sudo systemctl restart imagepod   # Restart ImagePod"
echo "  sudo systemctl status imagepod    # Check status"
echo "  docker-compose logs -f            # View logs"
echo ""
echo "🌐 Access ImagePod:"
echo "  API: http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo "  Health: http://localhost:8000/health"
