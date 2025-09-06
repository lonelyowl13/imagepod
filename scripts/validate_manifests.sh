#!/bin/bash

# ImagePod Kubernetes Manifests Validation Script
# This script validates YAML syntax without requiring a running Kubernetes cluster

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

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not available. Please install Python3 to validate YAML files."
    exit 1
fi

# Check if PyYAML is available
if ! python3 -c "import yaml" &> /dev/null; then
    print_error "PyYAML is not available. Please install it with: pip install PyYAML"
    exit 1
fi

print_status "Validating Kubernetes manifests..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
K8S_DIR="$PROJECT_DIR/k8s"

# Check if k8s directory exists
if [ ! -d "$K8S_DIR" ]; then
    print_error "k8s directory not found at $K8S_DIR"
    exit 1
fi

# Validate all YAML files in k8s directory
VALIDATION_FAILED=false

for yaml_file in "$K8S_DIR"/*.yaml; do
    if [ -f "$yaml_file" ]; then
        filename=$(basename "$yaml_file")
        print_status "Validating $filename..."
        
        if python3 -c "
import yaml
import sys
try:
    list(yaml.safe_load_all(open('$yaml_file')))
    print('✅ Valid')
except Exception as e:
    print(f'❌ Invalid: {e}')
    sys.exit(1)
" 2>/dev/null; then
            print_success "$filename is valid"
        else
            print_error "$filename has syntax errors"
            VALIDATION_FAILED=true
        fi
    fi
done

echo ""

if [ "$VALIDATION_FAILED" = true ]; then
    print_error "Some manifests have validation errors. Please fix them before deploying."
    exit 1
else
    print_success "All manifests are syntactically valid!"
    echo ""
    echo "🎉 Next steps:"
    echo "1. Copy this project to your Kubernetes master node"
    echo "2. Run: ./scripts/deploy_full_kubernetes.sh"
    echo ""
    echo "📋 Or deploy manually:"
    echo "  kubectl apply -f k8s/namespace.yaml"
    echo "  kubectl apply -f k8s/postgres.yaml"
    echo "  kubectl apply -f k8s/redis.yaml"
    echo "  kubectl apply -f k8s/api.yaml"
    echo "  kubectl apply -f k8s/ingress.yaml"
fi
