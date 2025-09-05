#!/bin/bash

# ImagePod GPU Workers Deployment Script
# This script deploys the GPU worker system to Kubernetes

set -e

# Configuration
NAMESPACE="imagepod"
REGISTRATION_TOKEN="your-registration-token-here"
API_ENDPOINT="http://imagepod-api.imagepod.svc.cluster.local:8000"

echo "🚀 Deploying ImagePod GPU Workers to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to Kubernetes
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster"
    exit 1
fi

echo "✅ Kubernetes connection verified"

# Create namespace and secrets
echo "📦 Creating namespace and secrets..."
kubectl apply -f k8s/namespace.yaml

# Update secrets with actual values
kubectl create secret generic imagepod-secrets \
    --from-literal=registration-token="$REGISTRATION_TOKEN" \
    --from-literal=api-key="your-api-key-here" \
    --namespace="$NAMESPACE" \
    --dry-run=client -o yaml | kubectl apply -f -

# Build and push GPU worker image
echo "🔨 Building GPU worker image..."
cd worker_agent
docker build -t imagepod/gpu-worker:latest .
cd ..

# If you have a registry, push the image
# docker push imagepod/gpu-worker:latest

# Deploy GPU worker DaemonSet
echo "🚀 Deploying GPU worker DaemonSet..."
kubectl apply -f k8s/gpu-worker-daemonset.yaml

# Deploy GPU worker services
echo "🌐 Deploying GPU worker services..."
kubectl apply -f k8s/gpu-worker-service.yaml

# Wait for pods to be ready
echo "⏳ Waiting for GPU worker pods to be ready..."
kubectl wait --for=condition=Ready pod -l app=imagepod-gpu-worker -n "$NAMESPACE" --timeout=300s

# Check deployment status
echo "📊 Checking deployment status..."
kubectl get pods -n "$NAMESPACE" -l app=imagepod-gpu-worker
kubectl get services -n "$NAMESPACE" -l app=imagepod-gpu-worker

# Show logs from one of the pods
echo "📋 Showing logs from GPU worker pod..."
POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app=imagepod-gpu-worker -o jsonpath='{.items[0].metadata.name}')
if [ -n "$POD_NAME" ]; then
    echo "Logs from pod: $POD_NAME"
    kubectl logs -n "$NAMESPACE" "$POD_NAME" --tail=20
fi

echo "✅ GPU Workers deployment completed!"
echo ""
echo "🔍 To check the status:"
echo "  kubectl get pods -n $NAMESPACE -l app=imagepod-gpu-worker"
echo "  kubectl logs -n $NAMESPACE -l app=imagepod-gpu-worker"
echo ""
echo "🌐 To access the API:"
echo "  kubectl port-forward -n $NAMESPACE svc/imagepod-gpu-worker 8080:8080"
echo ""
echo "📊 To monitor GPU usage:"
echo "  kubectl top nodes"
echo "  kubectl describe nodes | grep -A 5 'Allocated resources'"
