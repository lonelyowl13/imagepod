## ImagePod

ImagePod is a small FastAPI backend that provides a Runpod‑style API for running arbitrary jobs on remote GPUs. It exposes endpoints for authentication, jobs, pods, executors, templates, volumes and more, backed by Postgres, Redis, RabbitMQ and MinIO.

This is work in progress.

### Tech stack

- **Backend**: Python 3.12, FastAPI, Uvicorn
- **Database**: Postgres (SQLAlchemy + Alembic)
- **Messaging**: RabbitMQ
- **Cache/queue**: Redis
- **Infra tooling**: Docker Compose

### Running with Docker (all‑in‑one)

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```
2. Start everything (DB, cache, messaging, backend):
   ```bash
   docker compose up --build
   ```
3. The API will be available at `http://127.0.0.1:8000` and docs at `http://127.0.0.1:8000/docs`.

### Local development (debug mode)

1. Copy env files and tweak as needed:
   ```bash
   cp env.example .env
   ```
2. Create a virtualenv and install dependencies:
   ```bash
   ./run_local.sh install
   ```
3. Start infra (Postgres, Redis, RabbitMQ, MinIO):
   ```bash
   ./run_local.sh infra
   ```
4. Run the app with reload:
   ```bash
   ./run_local.sh run
   ```

Visit `http://127.0.0.1:8000/docs` for the interactive Swagger UI.
