#!/bin/bash

# ImagePod Secret Generation Script
# This script generates secure secrets for ImagePod configuration

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

# Function to generate a secure secret
generate_secret() {
    local length=${1:-32}
    if command -v python3 &> /dev/null; then
        python3 -c "import secrets; print(secrets.token_urlsafe($length))"
    elif command -v openssl &> /dev/null; then
        openssl rand -base64 $length
    else
        head -c $length /dev/urandom | base64
    fi
}

# Function to generate a random password
generate_password() {
    local length=${1:-16}
    if command -v python3 &> /dev/null; then
        python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*') for _ in range($length)))"
    else
        openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
    fi
}

print_status "Generating ImagePod secrets..."

# Generate secrets
SECRET_KEY=$(generate_secret 32)
POSTGRES_PASSWORD=$(generate_password 16)
REDIS_PASSWORD=$(generate_password 16)
REGISTRATION_TOKEN=$(generate_secret 32)
API_KEY=$(generate_secret 24)

# Create .env file with generated secrets
print_status "Creating .env file with generated secrets..."

cat > .env <<EOF
# ImagePod Configuration
# Generated on $(date)

# Security
SECRET_KEY=${SECRET_KEY}

# Database
POSTGRES_DB=imagepod
POSTGRES_USER=imagepod
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_URL=postgresql://imagepod:${POSTGRES_PASSWORD}@postgres:5432/imagepod

# Redis
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Worker Configuration
REGISTRATION_TOKEN=${REGISTRATION_TOKEN}
API_KEY=${API_KEY}

# Billing (Optional - Add your Stripe keys)
# STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
# STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key

# Email (Optional - Add your SMTP settings)
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your_email@gmail.com
# SMTP_PASSWORD=your_app_password
# SMTP_FROM_EMAIL=noreply@imagepod.com

# Monitoring (Optional)
# PROMETHEUS_ENABLED=true
# GRAFANA_ENABLED=true

# Kubernetes (Optional)
# KUBECONFIG_PATH=/path/to/your/kubeconfig
# K8S_NAMESPACE=imagepod

# Docker Registry (Optional)
# DOCKER_REGISTRY_URL=your-registry.com
# DOCKER_REGISTRY_USERNAME=your_username
# DOCKER_REGISTRY_PASSWORD=your_password
EOF

print_success "Secrets generated successfully!"
echo ""
echo "🔑 Generated Secrets:"
echo "  SECRET_KEY: ${SECRET_KEY:0:20}..."
echo "  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:0:8}..."
echo "  REDIS_PASSWORD: ${REDIS_PASSWORD:0:8}..."
echo "  REGISTRATION_TOKEN: ${REGISTRATION_TOKEN:0:20}..."
echo "  API_KEY: ${API_KEY:0:16}..."
echo ""
echo "📁 Configuration saved to: .env"
echo ""
echo "⚠️  IMPORTANT SECURITY NOTES:"
echo "  1. Keep this .env file secure and never commit it to version control"
echo "  2. Use different secrets for production environments"
echo "  3. Regularly rotate secrets in production"
echo "  4. Store production secrets in a secure secret management system"
echo ""
echo "🚀 Next steps:"
echo "  1. Review and customize the .env file"
echo "  2. Add your Stripe keys if using billing features"
echo "  3. Add your SMTP settings if using email features"
echo "  4. Start ImagePod: docker-compose up -d"
echo ""
echo "🔍 To view the full .env file:"
echo "  cat .env"
echo ""
echo "🔒 To regenerate secrets:"
echo "  ./scripts/generate_secrets.sh"
