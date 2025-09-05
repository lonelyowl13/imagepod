# ImagePod Full Kubernetes Infrastructure

This guide shows how to deploy the entire ImagePod infrastructure on Kubernetes, including the backend API, database, and GPU workers, all within the same cluster.

## 🏗️ **Kubernetes Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                          │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Backend API   │  │   PostgreSQL    │  │     Redis       │ │
│  │   (Deployment)  │  │   (StatefulSet) │  │   (Deployment)  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                     │                     │         │
│           └─────────────────────┼─────────────────────┘         │
│                                 │                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  GPU Worker 1   │  │  GPU Worker 2   │  │  GPU Worker N   │ │
│  │  (DaemonSet)    │  │  (DaemonSet)    │  │  (DaemonSet)    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 **Benefits of Full Kubernetes**

### **Networking Benefits**
- ✅ **Service Discovery** - Automatic DNS resolution between services
- ✅ **Load Balancing** - Built-in load balancing for backend API
- ✅ **Network Policies** - Fine-grained network security
- ✅ **Ingress** - External access control
- ✅ **No Public IPs Needed** - All communication within cluster

### **Operational Benefits**
- ✅ **Unified Management** - Single cluster for everything
- ✅ **Auto-scaling** - Scale backend and workers independently
- ✅ **Health Checks** - Automatic restart of failed pods
- ✅ **Rolling Updates** - Zero-downtime deployments
- ✅ **Resource Management** - CPU/memory limits and requests

## 📋 **Infrastructure Components**

### **Backend Services**
- **ImagePod API** - FastAPI application
- **PostgreSQL** - Database with persistent storage
- **Redis** - Cache and session storage
- **Prometheus** - Metrics collection
- **Grafana** - Monitoring dashboard

### **GPU Workers**
- **GPU Worker DaemonSet** - Runs on each GPU node
- **NVIDIA Device Plugin** - GPU resource management
- **GPU Job Executor** - Docker container execution

## 🛠️ **Deployment Steps**

### **Step 1: Set up Kubernetes Cluster**

```bash
# Install Kubernetes on all nodes
./scripts/setup_kubernetes.sh

# Join worker nodes to cluster
# (Follow the kubeadm join command from master)
```

### **Step 2: Deploy Backend Infrastructure**

```bash
# Deploy namespace and secrets
kubectl apply -f k8s/namespace.yaml

# Deploy PostgreSQL
kubectl apply -f k8s/postgres.yaml

# Deploy Redis
kubectl apply -f k8s/redis.yaml

# Deploy ImagePod API
kubectl apply -f k8s/api.yaml

# Deploy monitoring
kubectl apply -f k8s/monitoring.yaml
```

### **Step 3: Deploy GPU Workers**

```bash
# Deploy GPU workers
kubectl apply -f k8s/gpu-worker-daemonset.yaml

# Deploy GPU worker services
kubectl apply -f k8s/gpu-worker-service.yaml
```

### **Step 4: Set up Ingress (Optional)**

```bash
# Deploy ingress controller
kubectl apply -f k8s/ingress.yaml

# Configure external access
kubectl apply -f k8s/ingress-config.yaml
```

## 📁 **Kubernetes Manifests**

### **Namespace and Secrets**

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: imagepod
---
apiVersion: v1
kind: Secret
metadata:
  name: imagepod-secrets
  namespace: imagepod
type: Opaque
data:
  postgres-password: <base64-encoded>
  redis-password: <base64-encoded>
  secret-key: <base64-encoded>
  registration-token: <base64-encoded>
```

### **PostgreSQL StatefulSet**

```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: imagepod
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: imagepod
        - name: POSTGRES_USER
          value: imagepod
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: imagepod-secrets
              key: postgres-password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: imagepod
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

### **Redis Deployment**

```yaml
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: imagepod
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server", "--requirepass", "$(REDIS_PASSWORD)"]
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: imagepod-secrets
              key: redis-password
        ports:
        - containerPort: 6379
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: imagepod
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

### **ImagePod API Deployment**

```yaml
# k8s/api.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: imagepod-api
  namespace: imagepod
spec:
  replicas: 2
  selector:
    matchLabels:
      app: imagepod-api
  template:
    metadata:
      labels:
        app: imagepod-api
    spec:
      containers:
      - name: api
        image: imagepod/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: postgresql://imagepod:$(POSTGRES_PASSWORD)@postgres:5432/imagepod
        - name: REDIS_URL
          value: redis://:$(REDIS_PASSWORD)@redis:6379/0
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: imagepod-secrets
              key: secret-key
        - name: REGISTRATION_TOKEN
          valueFrom:
            secretKeyRef:
              name: imagepod-secrets
              key: registration-token
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: imagepod-api
  namespace: imagepod
spec:
  selector:
    app: imagepod-api
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

### **GPU Worker DaemonSet**

```yaml
# k8s/gpu-worker-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: imagepod-gpu-worker
  namespace: imagepod
spec:
  selector:
    matchLabels:
      app: imagepod-gpu-worker
  template:
    metadata:
      labels:
        app: imagepod-gpu-worker
    spec:
      nodeSelector:
        accelerator: nvidia-tesla-gpu
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - name: gpu-worker
        image: imagepod/gpu-worker:latest
        env:
        - name: API_ENDPOINT
          value: http://imagepod-api.imagepod.svc.cluster.local:8000
        - name: REGISTRATION_TOKEN
          valueFrom:
            secretKeyRef:
              name: imagepod-secrets
              key: registration-token
        resources:
          requests:
            nvidia.com/gpu: 1
            memory: "2Gi"
            cpu: "1"
          limits:
            nvidia.com/gpu: 1
            memory: "4Gi"
            cpu: "2"
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 8081
          name: websocket
        volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock
        - name: nvidia-driver
          mountPath: /usr/local/nvidia
          readOnly: true
      volumes:
      - name: docker-sock
        hostPath:
          path: /var/run/docker.sock
      - name: nvidia-driver
        hostPath:
          path: /usr/local/nvidia
```

### **Ingress Configuration**

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: imagepod-ingress
  namespace: imagepod
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: imagepod.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: imagepod-api
            port:
              number: 8000
```

## 🔧 **Service Discovery**

### **Internal Communication**

All services communicate using Kubernetes DNS:

```bash
# Backend API can reach:
postgres.imagepod.svc.cluster.local:5432
redis.imagepod.svc.cluster.local:6379

# GPU Workers can reach:
imagepod-api.imagepod.svc.cluster.local:8000

# External access (if ingress configured):
http://imagepod.local
```

### **Environment Variables**

```bash
# In API deployment
DATABASE_URL=postgresql://imagepod:password@postgres:5432/imagepod
REDIS_URL=redis://:password@redis:6379/0

# In GPU Worker deployment
API_ENDPOINT=http://imagepod-api.imagepod.svc.cluster.local:8000
```

## 🚀 **Deployment Script**

```bash
#!/bin/bash
# scripts/deploy_full_kubernetes.sh

set -e

echo "🚀 Deploying ImagePod Full Kubernetes Infrastructure..."

# Create namespace and secrets
kubectl apply -f k8s/namespace.yaml

# Deploy backend services
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/api.yaml

# Deploy GPU workers
kubectl apply -f k8s/gpu-worker-daemonset.yaml
kubectl apply -f k8s/gpu-worker-service.yaml

# Deploy monitoring
kubectl apply -f k8s/monitoring.yaml

# Deploy ingress (optional)
kubectl apply -f k8s/ingress.yaml

# Wait for deployments
kubectl wait --for=condition=Ready pod -l app=imagepod-api -n imagepod --timeout=300s
kubectl wait --for=condition=Ready pod -l app=imagepod-gpu-worker -n imagepod --timeout=300s

echo "✅ ImagePod Full Kubernetes Infrastructure deployed!"
echo ""
echo "🔍 Check status:"
echo "  kubectl get pods -n imagepod"
echo "  kubectl get services -n imagepod"
echo ""
echo "🌐 Access ImagePod:"
echo "  kubectl port-forward -n imagepod svc/imagepod-api 8000:8000"
echo "  Then visit: http://localhost:8000"
```

## 🔍 **Monitoring and Management**

### **Check Status**

```bash
# Check all pods
kubectl get pods -n imagepod

# Check services
kubectl get services -n imagepod

# Check GPU resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# Check logs
kubectl logs -n imagepod -l app=imagepod-api
kubectl logs -n imagepod -l app=imagepod-gpu-worker
```

### **Scaling**

```bash
# Scale API replicas
kubectl scale deployment imagepod-api -n imagepod --replicas=3

# Scale GPU workers (automatically scales with nodes)
kubectl label node <node-name> accelerator=nvidia-tesla-gpu
```

## 🎯 **Advantages of Full Kubernetes**

### **Networking**
- ✅ **No Public IPs Needed** - All communication within cluster
- ✅ **Service Discovery** - Automatic DNS resolution
- ✅ **Load Balancing** - Built-in load balancing
- ✅ **Network Policies** - Fine-grained security

### **Operations**
- ✅ **Unified Management** - Single cluster for everything
- ✅ **Auto-scaling** - Scale components independently
- ✅ **Health Checks** - Automatic restart of failed pods
- ✅ **Rolling Updates** - Zero-downtime deployments

### **Resource Management**
- ✅ **Resource Limits** - CPU/memory limits and requests
- ✅ **GPU Management** - NVIDIA Device Plugin integration
- ✅ **Storage Management** - Persistent volumes for database
- ✅ **Monitoring** - Built-in metrics and logging

## 🚀 **Quick Start**

1. **Set up Kubernetes cluster:**
   ```bash
   ./scripts/setup_kubernetes.sh
   ```

2. **Deploy full infrastructure:**
   ```bash
   ./scripts/deploy_full_kubernetes.sh
   ```

3. **Access ImagePod:**
   ```bash
   kubectl port-forward -n imagepod svc/imagepod-api 8000:8000
   ```

Your entire ImagePod infrastructure is now running on Kubernetes with automatic service discovery and no public IPs needed! 🎉
