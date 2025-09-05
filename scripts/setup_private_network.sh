#!/bin/bash

# ImagePod Private Network Setup Script
# This script helps configure networking for machines without public IPs

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

# Function to get user input
get_input() {
    local prompt="$1"
    local default="$2"
    local input
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        echo "${input:-$default}"
    else
        read -p "$prompt: " input
        echo "$input"
    fi
}

# Function to detect network interface
detect_interface() {
    # Try to find the main network interface
    local interface=$(ip route | grep default | awk '{print $5}' | head -n1)
    if [ -z "$interface" ]; then
        interface=$(ip link show | grep -E "^[0-9]+:" | grep -v lo | head -n1 | cut -d: -f2 | tr -d ' ')
    fi
    echo "$interface"
}

print_status "ImagePod Private Network Setup"
echo ""

# Get network configuration
NETWORK_TYPE=$(get_input "Choose network type (private/vpn/ssh/cloudflare)" "private")
INTERFACE=$(detect_interface)
PRIVATE_IP=$(get_input "Enter private IP for this machine" "")
SUBNET=$(get_input "Enter subnet (e.g., 10.0.0.0/24)" "10.0.0.0/24")

case $NETWORK_TYPE in
    "private")
        print_status "Setting up private network..."
        
        # Configure private IP
        if [ -n "$PRIVATE_IP" ]; then
            print_status "Configuring private IP: $PRIVATE_IP"
            sudo ip addr add $PRIVATE_IP/24 dev $INTERFACE 2>/dev/null || true
            sudo ip route add $SUBNET dev $INTERFACE 2>/dev/null || true
        fi
        
        # Configure firewall
        print_status "Configuring firewall..."
        sudo ufw allow from $SUBNET to any port 8000 2>/dev/null || true
        sudo ufw allow from $SUBNET to any port 8080 2>/dev/null || true
        sudo ufw allow out to $SUBNET 2>/dev/null || true
        
        print_success "Private network configured"
        ;;
        
    "vpn")
        print_status "Setting up WireGuard VPN..."
        
        # Install WireGuard
        if ! command -v wg &> /dev/null; then
            print_status "Installing WireGuard..."
            sudo apt update
            sudo apt install -y wireguard
        fi
        
        # Generate keys
        print_status "Generating WireGuard keys..."
        wg genkey | tee privatekey | wg pubkey > publickey
        PRIVATE_KEY=$(cat privatekey)
        PUBLIC_KEY=$(cat publickey)
        
        # Get VPN configuration
        VPN_IP=$(get_input "Enter VPN IP for this machine" "10.8.0.1")
        VPN_PORT=$(get_input "Enter VPN port" "51820")
        
        # Create WireGuard config
        print_status "Creating WireGuard configuration..."
        sudo tee /etc/wireguard/wg0.conf <<EOF
[Interface]
PrivateKey = $PRIVATE_KEY
Address = $VPN_IP/24
ListenPort = $VPN_PORT
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o $INTERFACE -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o $INTERFACE -j MASQUERADE
EOF
        
        # Start WireGuard
        print_status "Starting WireGuard..."
        sudo systemctl enable wg-quick@wg0
        sudo systemctl start wg-quick@wg0
        
        print_success "WireGuard VPN configured"
        print_warning "Public key: $PUBLIC_KEY"
        print_warning "Add this to other machines' WireGuard configs"
        ;;
        
    "ssh")
        print_status "Setting up SSH tunneling..."
        
        JUMP_SERVER=$(get_input "Enter jump server address" "")
        JUMP_USER=$(get_input "Enter jump server username" "$USER")
        
        if [ -n "$JUMP_SERVER" ]; then
            print_status "Creating SSH tunnel..."
            ssh -f -N -L 8000:localhost:8000 $JUMP_USER@$JUMP_SERVER
            
            print_success "SSH tunnel created"
            print_warning "Backend will be accessible at: $JUMP_SERVER:8000"
        fi
        ;;
        
    "cloudflare")
        print_status "Setting up Cloudflare tunnel..."
        
        # Install cloudflared
        if ! command -v cloudflared &> /dev/null; then
            print_status "Installing cloudflared..."
            wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
            sudo dpkg -i cloudflared-linux-amd64.deb
        fi
        
        # Login to Cloudflare
        print_status "Please login to Cloudflare..."
        cloudflared tunnel login
        
        # Create tunnel
        TUNNEL_NAME=$(get_input "Enter tunnel name" "imagepod-backend")
        HOSTNAME=$(get_input "Enter hostname (e.g., imagepod.yourdomain.com)" "")
        
        if [ -n "$HOSTNAME" ]; then
            print_status "Creating Cloudflare tunnel..."
            cloudflared tunnel create $TUNNEL_NAME
            
            # Configure tunnel
            mkdir -p ~/.cloudflared
            cat > ~/.cloudflared/config.yml <<EOF
tunnel: $TUNNEL_NAME
credentials-file: /home/$USER/.cloudflared/$TUNNEL_NAME.json

ingress:
  - hostname: $HOSTNAME
    service: http://localhost:8000
  - service: http_status:404
EOF
            
            print_success "Cloudflare tunnel configured"
            print_warning "Start tunnel with: cloudflared tunnel run $TUNNEL_NAME"
        fi
        ;;
        
    *)
        print_error "Invalid network type: $NETWORK_TYPE"
        exit 1
        ;;
esac

# Configure ImagePod
print_status "Configuring ImagePod for private network..."

# Determine API endpoint
case $NETWORK_TYPE in
    "private")
        API_ENDPOINT="http://$PRIVATE_IP:8000"
        ;;
    "vpn")
        API_ENDPOINT="http://$VPN_IP:8000"
        ;;
    "ssh")
        API_ENDPOINT="http://$JUMP_SERVER:8000"
        ;;
    "cloudflare")
        API_ENDPOINT="https://$HOSTNAME"
        ;;
esac

# Create configuration file
print_status "Creating network configuration..."
cat > network_config.env <<EOF
# ImagePod Network Configuration
# Generated on $(date)

# Network Type
NETWORK_TYPE=$NETWORK_TYPE

# API Configuration
API_ENDPOINT=$API_ENDPOINT
API_HOST=0.0.0.0
API_PORT=8000

# Network Details
PRIVATE_IP=$PRIVATE_IP
SUBNET=$SUBNET
INTERFACE=$INTERFACE

# VPN Details (if applicable)
VPN_IP=$VPN_IP
VPN_PORT=$VPN_PORT
PUBLIC_KEY=$PUBLIC_KEY

# SSH Tunnel Details (if applicable)
JUMP_SERVER=$JUMP_SERVER
JUMP_USER=$JUMP_USER

# Cloudflare Tunnel Details (if applicable)
TUNNEL_NAME=$TUNNEL_NAME
HOSTNAME=$HOSTNAME
EOF

print_success "Network configuration saved to: network_config.env"
echo ""
echo "🎉 Private network setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Review network configuration: cat network_config.env"
echo "2. Deploy ImagePod backend: ./scripts/setup_backend_only.sh"
echo "3. Configure GPU workers with API_ENDPOINT=$API_ENDPOINT"
echo ""
echo "🔍 Test connectivity:"
echo "  curl $API_ENDPOINT/health"
echo ""
echo "📚 For more details, see: PRIVATE_NETWORK_SETUP.md"
