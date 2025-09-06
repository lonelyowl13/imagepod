# ImagePod Port Configuration

This document describes the port configuration for ImagePod services to avoid conflicts with other services on the machine.

## 🔌 **Port Mapping**

### **Internal Container Ports (Unchanged)**
- **ImagePod API**: `8000` (container internal)
- **PostgreSQL**: `5432` (container internal)
- **Redis**: `6379` (container internal)

### **Kubernetes Service Ports (Modified)**
- **ImagePod API**: `8000` (ClusterIP service)
- **PostgreSQL**: `15432` (ClusterIP service) - *was 5432*
- **Redis**: `16379` (ClusterIP service) - *was 6379*

### **External Access Ports (Non-Standard)**
- **NodePort API**: `38080` (NodePort service) - *was 30080*
- **LoadBalancer API**: `18080` (LoadBalancer service)
- **Ingress**: Standard HTTP/HTTPS ports (80/443)

## 🚀 **Access Methods**

### **1. Port Forwarding (Development)**
```bash
# API access
kubectl port-forward -n imagepod svc/imagepod-api 8000:8000

# Database access (if needed)
kubectl port-forward -n imagepod svc/postgres 15432:15432

# Redis access (if needed)
kubectl port-forward -n imagepod svc/redis 16379:16379
```

### **2. NodePort (Direct Access)**
```bash
# Access API via NodePort
curl http://<node-ip>:38080/health
```

### **3. LoadBalancer (Cloud/External)**
```bash
# Access API via LoadBalancer
curl http://<loadbalancer-ip>:18080/health
```

### **4. Ingress (Domain-based)**
```bash
# Add to /etc/hosts
echo "<node-ip> imagepod.local" >> /etc/hosts
echo "<node-ip> api.imagepod.local" >> /etc/hosts

# Access via domain
curl http://imagepod.local/health
curl http://api.imagepod.local/health
```

## 🔧 **Configuration Changes**

### **Database Connection URLs**
The API now connects to databases using the new service ports:
- **PostgreSQL**: `postgresql://imagepod:password@postgres:15432/imagepod`
- **Redis**: `redis://:password@redis:16379/0`

### **Service Discovery**
Within the Kubernetes cluster, services communicate using:
- **API → PostgreSQL**: `postgres:15432`
- **API → Redis**: `redis:16379`

## 🛡️ **Security Benefits**

### **Port Conflict Avoidance**
- **PostgreSQL**: `15432` instead of standard `5432`
- **Redis**: `16379` instead of standard `6379`
- **API NodePort**: `38080` instead of standard `30080`

### **Reduced Attack Surface**
- Non-standard ports make services less discoverable
- Reduces risk of automated attacks on common ports
- Allows coexistence with other services

## 📋 **Port Summary**

| Service | Internal Port | Service Port | External Port | Access Method |
|---------|---------------|--------------|---------------|---------------|
| API | 8000 | 8000 | 38080 (NodePort)<br>18080 (LoadBalancer) | HTTP |
| PostgreSQL | 5432 | 15432 | - | Cluster Internal |
| Redis | 6379 | 16379 | - | Cluster Internal |

## 🔍 **Troubleshooting**

### **Check Service Ports**
```bash
kubectl get services -n imagepod
kubectl describe service imagepod-api -n imagepod
```

### **Test Connectivity**
```bash
# Test API
curl http://localhost:8000/health

# Test database (from within cluster)
kubectl exec -it <api-pod> -- psql postgresql://imagepod:password@postgres:15432/imagepod

# Test Redis (from within cluster)
kubectl exec -it <api-pod> -- redis-cli -h redis -p 16379 -a password ping
```

### **Port Conflicts**
If you encounter port conflicts:
1. Check what's using the port: `netstat -tulpn | grep :<port>`
2. Modify the service port in the YAML files
3. Redeploy the services: `kubectl apply -f k8s/`

## 📝 **Notes**

- **Internal ports** (container ports) remain standard for compatibility
- **Service ports** are modified to avoid conflicts
- **External ports** use non-standard ranges for security
- All configurations are in the `k8s/` directory
- Changes are automatically applied when redeploying
