#!/bin/bash

# ImagePod Setup Script
set -e

echo "🚀 Setting up ImagePod backend..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your configuration before continuing."
    echo "   Especially update the SECRET_KEY and database credentials."
    read -p "Press Enter to continue after editing .env file..."
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p data/postgres
mkdir -p data/redis
mkdir -p data/prometheus
mkdir -p data/grafana

# Set proper permissions
echo "🔐 Setting permissions..."
chmod 755 logs
chmod 755 data

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
echo "🔍 Checking service health..."
if ! docker-compose ps | grep -q "postgres.*Up"; then
    echo "❌ PostgreSQL failed to start"
    exit 1
fi

if ! docker-compose ps | grep -q "redis.*Up"; then
    echo "❌ Redis failed to start"
    exit 1
fi

echo "✅ Services are running!"

# Run database migrations
echo "🗄️  Running database migrations..."
docker-compose run --rm api alembic upgrade head

# Start the API service
echo "🚀 Starting API service..."
docker-compose up -d api

# Wait for API to be ready
echo "⏳ Waiting for API to be ready..."
sleep 5

# Check API health
echo "🔍 Checking API health..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is healthy!"
else
    echo "❌ API health check failed"
    echo "Check logs with: docker-compose logs api"
    exit 1
fi

# Start monitoring services
echo "📊 Starting monitoring services..."
docker-compose up -d prometheus grafana

echo ""
echo "🎉 ImagePod setup complete!"
echo ""
echo "📋 Service URLs:"
echo "   API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   Grafana: http://localhost:3000 (admin/admin)"
echo "   Prometheus: http://localhost:9090"
echo ""
echo "🔧 Useful commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart API: docker-compose restart api"
echo "   Database shell: docker-compose exec postgres psql -U imagepod -d imagepod"
echo ""
echo "📚 Next steps:"
echo "   1. Create a user account via the API"
echo "   2. Set up your first job template"
echo "   3. Configure worker pools"
echo "   4. Set up billing accounts"
echo ""
echo "Happy coding! 🚀"
