#!/bin/bash

# ImagePod Full Kubernetes Infrastructure Deployment Script
# This script deploys the entire ImagePod infrastructure on Kubernetes

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

echo "🚀 Deploying ImagePod Full Kubernetes Infrastructure..."
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to Kubernetes
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

print_success "Kubernetes connection verified"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Create namespace and secrets
print_status "Creating namespace and secrets..."
kubectl apply -f "$PROJECT_DIR/k8s/namespace.yaml"

# Generate secrets if they don't exist
if [ ! -f "$PROJECT_DIR/.env" ]; then
    print_status "Generating secrets..."
    cd "$PROJECT_DIR"
    ./scripts/generate_secrets.sh
fi

# Update secrets in Kubernetes
print_status "Updating Kubernetes secrets..."
if [ -f "$PROJECT_DIR/.env" ]; then
    # Extract secrets from .env file
    source "$PROJECT_DIR/.env"
    
    # Create or update secrets
    kubectl create secret generic imagepod-secrets \
        --from-literal=postgres-password="$POSTGRES_PASSWORD" \
        --from-literal=redis-password="$REDIS_PASSWORD" \
        --from-literal=secret-key="$SECRET_KEY" \
        --from-literal=registration-token="$REGISTRATION_TOKEN" \
        --namespace=imagepod \
        --dry-run=client -o yaml | kubectl apply -f -
fi

# Deploy backend services
print_status "Deploying PostgreSQL..."
kubectl apply -f "$PROJECT_DIR/k8s/postgres.yaml"

print_status "Deploying Redis..."
kubectl apply -f "$PROJECT_DIR/k8s/redis.yaml"

print_status "Deploying ImagePod API..."
kubectl apply -f "$PROJECT_DIR/k8s/api.yaml"

# Deploy GPU workers
print_status "Deploying GPU workers..."
kubectl apply -f "$PROJECT_DIR/k8s/gpu-worker-daemonset.yaml"
kubectl apply -f "$PROJECT_DIR/k8s/gpu-worker-service.yaml"

# Deploy ingress (optional)
print_status "Deploying ingress..."
kubectl apply -f "$PROJECT_DIR/k8s/ingress.yaml"

# Wait for deployments
print_status "Waiting for deployments to be ready..."

# Wait for PostgreSQL
print_status "Waiting for PostgreSQL..."
kubectl wait --for=condition=Ready pod -l app=postgres -n imagepod --timeout=300s

# Wait for Redis
print_status "Waiting for Redis..."
kubectl wait --for=condition=Ready pod -l app=redis -n imagepod --timeout=300s

# Wait for API
print_status "Waiting for ImagePod API..."
kubectl wait --for=condition=Ready pod -l app=imagepod-api -n imagepod --timeout=300s

# Wait for GPU workers
print_status "Waiting for GPU workers..."
kubectl wait --for=condition=Ready pod -l app=imagepod-gpu-worker -n imagepod --timeout=300s

# Check deployment status
print_status "Checking deployment status..."
echo ""
echo "=== Pods ==="
kubectl get pods -n imagepod
echo ""
echo "=== Services ==="
kubectl get services -n imagepod
echo ""
echo "=== GPU Resources ==="
kubectl describe nodes | grep -A 5 "Allocated resources" || true

# Show logs from API pod
print_status "Showing API logs..."
API_POD=$(kubectl get pods -n imagepod -l app=imagepod-api -o jsonpath='{.items[0].metadata.name}')
if [ -n "$API_POD" ]; then
    echo "Logs from API pod: $API_POD"
    kubectl logs -n imagepod "$API_POD" --tail=10
fi

print_success "ImagePod Full Kubernetes Infrastructure deployed successfully!"
echo ""
echo "🎉 Deployment completed!"
echo ""
echo "🔍 Check status:"
echo "  kubectl get pods -n imagepod"
echo "  kubectl get services -n imagepod"
echo "  kubectl get ingress -n imagepod"
echo ""
echo "🌐 Access ImagePod:"
echo "  # Port forward to local machine"
echo "  kubectl port-forward -n imagepod svc/imagepod-api 8000:8000"
echo "  # Then visit: http://localhost:8000"
echo ""
echo "  # Or access via NodePort (if available)"
echo "  # Visit: http://<node-ip>:30080"
echo ""
echo "📊 Monitor GPU workers:"
echo "  kubectl get pods -n imagepod -l app=imagepod-gpu-worker"
echo "  kubectl logs -n imagepod -l app=imagepod-gpu-worker"
echo ""
echo "🔧 Scale API replicas:"
echo "  kubectl scale deployment imagepod-api -n imagepod --replicas=3"
echo ""
echo "📚 View API documentation:"
echo "  kubectl port-forward -n imagepod svc/imagepod-api 8000:8000"
echo "  # Then visit: http://localhost:8000/docs"
echo ""
echo "🎯 Test the system:"
echo "  # Register a GPU node"
echo "  curl -X POST \"http://localhost:8000/gpu-workers/nodes/register\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"node_name\": \"test-gpu-node\", \"gpu_count\": 1}'"
echo ""
echo "✅ Your ImagePod infrastructure is now running on Kubernetes!"
