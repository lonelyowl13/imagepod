# ImagePod Makefile
# Provides convenient commands for development and deployment

.PHONY: help setup start stop restart logs test clean build deploy

# Default target
help:
	@echo "ImagePod - RunPod Clone Backend"
	@echo ""
	@echo "Available commands:"
	@echo "  setup     - Initial setup (copy env, create dirs)"
	@echo "  start     - Start all services"
	@echo "  stop      - Stop all services"
	@echo "  restart   - Restart all services"
	@echo "  logs      - View logs"
	@echo "  test      - Run API tests"
	@echo "  clean     - Clean up containers and volumes"
	@echo "  build     - Build Docker images"
	@echo "  deploy    - Deploy to production"
	@echo "  db-init   - Initialize database"
	@echo "  db-migrate - Run database migrations"
	@echo "  shell     - Open shell in API container"
	@echo "  psql      - Connect to PostgreSQL"

# Setup
setup:
	@echo "🚀 Setting up ImagePod..."
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "⚠️  Please edit .env file with your configuration"; \
	fi
	@mkdir -p logs data/postgres data/redis data/prometheus data/grafana
	@echo "✅ Setup complete"

# Start services
start:
	@echo "🐳 Starting ImagePod services..."
	docker-compose up -d
	@echo "✅ Services started"
	@echo "📋 Access URLs:"
	@echo "   API: http://localhost:8000"
	@echo "   Docs: http://localhost:8000/docs"
	@echo "   Grafana: http://localhost:3000"

# Stop services
stop:
	@echo "🛑 Stopping ImagePod services..."
	docker-compose down
	@echo "✅ Services stopped"

# Restart services
restart: stop start

# View logs
logs:
	docker-compose logs -f

# Run tests
test:
	@echo "🧪 Running API tests..."
	python test_api.py

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleanup complete"

# Build images
build:
	@echo "🔨 Building Docker images..."
	docker-compose build
	@echo "✅ Build complete"

# Database initialization
db-init:
	@echo "🗄️  Initializing database..."
	docker-compose run --rm api python scripts/init_db.py
	@echo "✅ Database initialized"

# Database migrations
db-migrate:
	@echo "🗄️  Running database migrations..."
	docker-compose run --rm api alembic upgrade head
	@echo "✅ Migrations complete"

# Open shell in API container
shell:
	docker-compose exec api /bin/bash

# Connect to PostgreSQL
psql:
	docker-compose exec postgres psql -U imagepod -d imagepod

# Development mode
dev:
	@echo "🔧 Starting development mode..."
	docker-compose up -d postgres redis
	@echo "⏳ Waiting for services..."
	sleep 5
	@echo "🚀 Starting API in development mode..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production deployment
deploy:
	@echo "🚀 Deploying to production..."
	@echo "⚠️  Make sure to:"
	@echo "   1. Update .env with production values"
	@echo "   2. Set DEBUG=false"
	@echo "   3. Use strong SECRET_KEY"
	@echo "   4. Configure proper database credentials"
	@echo "   5. Set up SSL certificates"
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "✅ Production deployment complete"

# Health check
health:
	@echo "🔍 Checking service health..."
	@curl -f http://localhost:8000/health || echo "❌ API not healthy"
	@docker-compose ps

# Backup database
backup:
	@echo "💾 Backing up database..."
	docker-compose exec postgres pg_dump -U imagepod imagepod > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup complete"

# Restore database
restore:
	@echo "📥 Restoring database..."
	@read -p "Enter backup file path: " file; \
	docker-compose exec -T postgres psql -U imagepod -d imagepod < $$file
	@echo "✅ Restore complete"

# Monitor resources
monitor:
	@echo "📊 Monitoring resources..."
	docker stats

# Update dependencies
update:
	@echo "📦 Updating dependencies..."
	docker-compose run --rm api pip install --upgrade -r requirements.txt
	@echo "✅ Dependencies updated"
