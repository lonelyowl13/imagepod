# ImagePod - RunPod Clone Backend

A comprehensive FastAPI backend service for AI/ML job processing, compatible with RunPod serverless endpoints. This service provides authentication, billing, job processing, and worker scaling capabilities.

## Features

- **Authentication & Authorization**: JWT-based authentication with user management
- **Job Processing**: RunPod-compatible job execution with templates
- **Billing System**: Usage tracking, payment processing with Stripe integration
- **Worker Scaling**: Auto-scaling worker pools with Kubernetes/Docker support
- **Database**: PostgreSQL with Redis caching
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **API Documentation**: Auto-generated OpenAPI/Swagger docs

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   PostgreSQL    │    │     Redis       │
│                 │◄──►│                 │    │                 │
│ - Authentication│    │ - Users         │    │ - Caching       │
│ - Job Management│    │ - Jobs          │    │ - Sessions      │
│ - Billing       │    │ - Billing       │    │ - Rate Limiting │
│ - Worker Mgmt   │    │ - Workers       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│   Worker Pools  │    │   Monitoring    │
│                 │    │                 │
│ - Kubernetes    │    │ - Prometheus    │
│ - Docker        │    │ - Grafana       │
│ - AWS           │    │ - Health Checks │
└─────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 15+ (if running locally)
- Redis 7+ (if running locally)

### Using Docker Compose (Recommended)

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd imagepod
   cp env.example .env
   # Edit .env with your configuration
   ```

2. **Start services**:
   ```bash
   docker-compose up -d
   ```

3. **Access services**:
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090

### Local Development

1. **Setup environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Setup database**:
   ```bash
   # Start PostgreSQL and Redis
   docker-compose up -d postgres redis
   
   # Run migrations
   alembic upgrade head
   ```

3. **Run the application**:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `GET /auth/me` - Get current user info
- `POST /auth/regenerate-api-key` - Regenerate API key

### Jobs
- `POST /jobs/` - Create new job
- `GET /jobs/` - Get user jobs
- `GET /jobs/{job_id}` - Get specific job
- `GET /jobs/{job_id}/runpod` - Get job in RunPod format
- `PUT /jobs/{job_id}/status` - Update job status (workers)

### Job Templates
- `POST /jobs/templates/` - Create job template
- `GET /jobs/templates/` - Get public templates
- `GET /jobs/templates/my/` - Get user templates

### Billing
- `POST /billing/accounts/` - Create billing account
- `GET /billing/accounts/` - Get user accounts
- `POST /billing/payment-intents/` - Create payment intent
- `GET /billing/accounts/{id}/transactions/` - Get transactions

### Workers (Admin)
- `POST /workers/pools/` - Create worker pool
- `GET /workers/pools/` - Get worker pools
- `PUT /workers/pools/{id}/scale` - Scale worker pool
- `POST /workers/auto-scale` - Trigger auto-scaling

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/imagepod
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Keys
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key

# AWS (for worker scaling)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# Kubernetes (for worker scaling)
KUBECONFIG_PATH=/path/to/kubeconfig

# Docker
DOCKER_REGISTRY=your-registry.com
DOCKER_IMAGE_PREFIX=imagepod

# Environment
ENVIRONMENT=development
DEBUG=true
```

## Database Schema

### Core Tables
- **users**: User accounts and authentication
- **jobs**: Job execution records
- **job_templates**: Reusable job configurations
- **billing_accounts**: User billing accounts
- **transactions**: Payment and usage transactions
- **usage**: Detailed usage tracking
- **worker_pools**: Worker pool configurations
- **workers**: Individual worker instances

## RunPod Compatibility

The API provides RunPod serverless endpoint compatibility:

```python
# RunPod-style job creation
import requests

response = requests.post(
    "http://localhost:8000/jobs/",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={
        "template_id": 1,
        "input_data": {"prompt": "Generate an image of a cat"}
    }
)

# Get job status in RunPod format
job_response = requests.get(
    f"http://localhost:8000/jobs/{job_id}/runpod",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)
```

## Worker Scaling

### Supported Infrastructure
- **Kubernetes**: Auto-scaling with HPA
- **Docker**: Container-based workers
- **AWS**: EC2/ECS integration

### Auto-scaling Configuration
```python
{
    "auto_scaling": True,
    "scale_up_threshold": 0.8,    # 80% utilization
    "scale_down_threshold": 0.2,  # 20% utilization
    "scale_up_cooldown": 300,     # 5 minutes
    "scale_down_cooldown": 600    # 10 minutes
}
```

## Monitoring

### Metrics
- Job execution metrics
- Worker utilization
- Billing and usage statistics
- API performance metrics

### Health Checks
- Database connectivity
- Redis connectivity
- Worker health status
- External service status

## Development

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Testing
```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=app
```

### Code Quality
```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

## Deployment

### Production Considerations
1. **Security**: Change default secrets, enable HTTPS
2. **Database**: Use managed PostgreSQL service
3. **Caching**: Use managed Redis service
4. **Monitoring**: Set up proper alerting
5. **Scaling**: Configure load balancers
6. **Backup**: Implement database backups

### Kubernetes Deployment
```yaml
# Example Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: imagepod-api
spec:
  replicas: 3
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
        image: imagepod:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: imagepod-secrets
              key: database-url
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the API docs at `/docs`
