# ImagePod Private Network Setup Guide

This guide shows how to deploy ImagePod on machines without public IPs using various networking solutions.

## 🌐 **Network Architecture Options**

### **Option 1: Private Network (Recommended)**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Backend       │    │  GPU Worker 1   │    │  GPU Worker 2   │
│   10.0.0.100    │    │   10.0.0.101    │    │   10.0.0.102    │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ ImagePod    │ │◄──►│ │ GPU Worker  │ │    │ │ GPU Worker  │ │
│ │ API         │ │    │ │ Agent       │ │    │ │ Agent       │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Option 2: VPN Connection**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Backend       │    │  GPU Worker 1   │    │  GPU Worker 2   │
│   VPN: 10.8.0.1 │    │  VPN: 10.8.0.2  │    │  VPN: 10.8.0.3  │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ ImagePod    │ │◄──►│ │ GPU Worker  │ │    │ │ GPU Worker  │ │
│ │ API         │ │    │ │ Agent       │ │    │ │ Agent       │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Option 3: SSH Tunneling**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Jump Server   │    │   Backend       │    │  GPU Worker 1   │
│   (Public IP)   │    │   (Private)     │    │   (Private)     │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ SSH Tunnel  │ │◄──►│ │ ImagePod    │ │◄──►│ │ GPU Worker  │ │
│ │ Port 8000   │ │    │ │ API         │ │    │ │ Agent       │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 **Option 1: Private Network Setup**

### **Step 1: Configure Private Network**

On each machine, configure a private network interface:

```bash
# On Backend Server (10.0.0.100)
sudo ip addr add 10.0.0.100/24 dev eth0
sudo ip route add 10.0.0.0/24 dev eth0

# On GPU Worker 1 (10.0.0.101)
sudo ip addr add 10.0.0.101/24 dev eth0
sudo ip route add 10.0.0.0/24 dev eth0

# On GPU Worker 2 (10.0.0.102)
sudo ip addr add 10.0.0.102/24 dev eth0
sudo ip route add 10.0.0.0/24 dev eth0
```

### **Step 2: Configure Firewall**

```bash
# On Backend Server
sudo ufw allow from 10.0.0.0/24 to any port 8000
sudo ufw allow out to 10.0.0.0/24

# On GPU Workers
sudo ufw allow from 10.0.0.0/24 to any port 8080
sudo ufw allow out to 10.0.0.0/24
```

### **Step 3: Deploy ImagePod**

```bash
# On Backend Server
export API_HOST=10.0.0.100
./scripts/setup_backend_only.sh

# On GPU Workers
export API_ENDPOINT="http://10.0.0.100:8000"
export REGISTRATION_TOKEN="your-secure-token"
./scripts/setup_gpu_worker_simple.sh
```

## 🔐 **Option 2: VPN Setup (WireGuard)**

### **Step 1: Install WireGuard**

```bash
# On all machines
sudo apt update
sudo apt install wireguard
```

### **Step 2: Generate Keys**

```bash
# On Backend Server
wg genkey | tee privatekey | wg pubkey > publickey
BACKEND_PRIVATE=$(cat privatekey)
BACKEND_PUBLIC=$(cat publickey)

# On GPU Worker 1
wg genkey | tee privatekey | wg pubkey > publickey
WORKER1_PRIVATE=$(cat privatekey)
WORKER1_PUBLIC=$(cat publickey)
```

### **Step 3: Configure WireGuard**

**Backend Server (`/etc/wireguard/wg0.conf`):**
```ini
[Interface]
PrivateKey = BACKEND_PRIVATE
Address = 10.8.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = WORKER1_PUBLIC
AllowedIPs = 10.8.0.2/32
```

**GPU Worker 1 (`/etc/wireguard/wg0.conf`):**
```ini
[Interface]
PrivateKey = WORKER1_PRIVATE
Address = 10.8.0.2/24
DNS = 8.8.8.8

[Peer]
PublicKey = BACKEND_PUBLIC
Endpoint = BACKEND_PUBLIC_IP:51820
AllowedIPs = 10.8.0.0/24
PersistentKeepalive = 25
```

### **Step 4: Start VPN**

```bash
# On all machines
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
```

### **Step 5: Deploy ImagePod**

```bash
# On Backend Server
export API_HOST=10.8.0.1
./scripts/setup_backend_only.sh

# On GPU Workers
export API_ENDPOINT="http://10.8.0.1:8000"
export REGISTRATION_TOKEN="your-secure-token"
./scripts/setup_gpu_worker_simple.sh
```

## 🔗 **Option 3: SSH Tunneling**

### **Step 1: Set up SSH Tunnel**

```bash
# From a machine with public IP (jump server)
ssh -L 8000:backend-private-ip:8000 user@jump-server

# Or create a persistent tunnel
ssh -f -N -L 8000:backend-private-ip:8000 user@jump-server
```

### **Step 2: Configure ImagePod**

```bash
# On Backend Server
export API_HOST=0.0.0.0
./scripts/setup_backend_only.sh

# On GPU Workers (connect through jump server)
export API_ENDPOINT="http://jump-server-public-ip:8000"
export REGISTRATION_TOKEN="your-secure-token"
./scripts/setup_gpu_worker_simple.sh
```

## 🌍 **Option 4: Cloudflare Tunnel (Free)**

### **Step 1: Install Cloudflare Tunnel**

```bash
# On Backend Server
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

### **Step 2: Authenticate**

```bash
# Login to Cloudflare
cloudflared tunnel login
```

### **Step 3: Create Tunnel**

```bash
# Create tunnel
cloudflared tunnel create imagepod-backend

# Configure tunnel
cat > ~/.cloudflared/config.yml <<EOF
tunnel: imagepod-backend
credentials-file: /home/$USER/.cloudflared/imagepod-backend.json

ingress:
  - hostname: imagepod.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF
```

### **Step 4: Start Tunnel**

```bash
# Start tunnel
cloudflared tunnel run imagepod-backend
```

### **Step 5: Deploy ImagePod**

```bash
# On Backend Server
export API_HOST=0.0.0.0
./scripts/setup_backend_only.sh

# On GPU Workers
export API_ENDPOINT="https://imagepod.yourdomain.com"
export REGISTRATION_TOKEN="your-secure-token"
./scripts/setup_gpu_worker_simple.sh
```

## 🔧 **Network Testing**

### **Test Connectivity**

```bash
# Test backend connectivity
curl http://backend-ip:8000/health

# Test worker connectivity
curl http://worker-ip:8080/health

# Test from worker to backend
curl http://backend-ip:8000/gpu-workers/nodes/
```

### **Check Network Routes**

```bash
# Check routing table
ip route show

# Test connectivity
ping backend-ip
telnet backend-ip 8000
```

## 🛠️ **Troubleshooting**

### **Common Issues**

#### **1. Connection Refused**
```bash
# Check if service is running
sudo systemctl status imagepod

# Check if port is open
sudo netstat -tulpn | grep :8000

# Check firewall
sudo ufw status
```

#### **2. Network Unreachable**
```bash
# Check network configuration
ip addr show
ip route show

# Test basic connectivity
ping backend-ip
```

#### **3. DNS Resolution Issues**
```bash
# Use IP addresses instead of hostnames
export API_ENDPOINT="http://10.0.0.100:8000"

# Or add to /etc/hosts
echo "10.0.0.100 backend-server" | sudo tee -a /etc/hosts
```

## 📋 **Configuration Examples**

### **Backend Configuration**

```bash
# .env file for backend
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# For private network
API_HOST=10.0.0.100

# For VPN
API_HOST=10.8.0.1
```

### **GPU Worker Configuration**

```bash
# .env file for GPU worker
API_ENDPOINT=http://10.0.0.100:8000
REGISTRATION_TOKEN=your-secure-token

# For VPN
API_ENDPOINT=http://10.8.0.1:8000

# For SSH tunnel
API_ENDPOINT=http://jump-server:8000

# For Cloudflare tunnel
API_ENDPOINT=https://imagepod.yourdomain.com
```

## 🎯 **Recommended Approach**

For machines without public IPs, I recommend:

1. **Private Network** - If machines are in the same data center
2. **VPN (WireGuard)** - If machines are in different locations
3. **SSH Tunneling** - If you have a jump server with public IP
4. **Cloudflare Tunnel** - If you want a public endpoint

Choose the option that best fits your infrastructure and security requirements!

## 🚀 **Quick Start**

1. **Choose your networking option**
2. **Set up the network connection**
3. **Configure ImagePod with the correct IPs**
4. **Deploy and test**

Your ImagePod deployment will work perfectly without public IPs! 🌐
