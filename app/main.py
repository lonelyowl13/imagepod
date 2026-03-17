from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from importlib.metadata import version as _pkg_version, PackageNotFoundError
import uvicorn
from app.config import settings

try:
    __version__ = _pkg_version("imagepod")
except PackageNotFoundError:
    __version__ = "0.0.0"
from app.database import engine, Base
from app.api import auth, jobs, endpoints, templates, executors, executor_api, volumes, runpod, pods
from app.api import frp as frp_router
from app.rabbitmq import connect as rabbitmq_connect


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""

    print("Starting ImagePod backend...")

    Base.metadata.create_all(bind=engine)
    print("Database tables created")

    app.state.rabbitmq = None
    try:
        app.state.rabbitmq = await rabbitmq_connect(settings.get_rabbitmq_url())
        print("RabbitMQ connected")
    except Exception as e:
        print(f"RabbitMQ connection failed: {e} (job long-poll will fall back to timeout-only)")

    print("ImagePod backend is ready!")

    yield

    if app.state.rabbitmq:
        await app.state.rabbitmq.close()
        print("RabbitMQ connection closed")

    if settings.test:
        Base.metadata.drop_all(bind=engine)
        print("Database tables nuked")
        print("Shutting down ImagePod backend...")


app = FastAPI(
    title="ImagePod API",
    description="Runpod-esque backend to run random stuff on your friend's gpu",
    version=__version__,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(endpoints.router)
app.include_router(templates.router)
app.include_router(executors.router)
app.include_router(executor_api.router)
app.include_router(volumes.router)
app.include_router(runpod.router)
app.include_router(pods.router)
app.include_router(frp_router.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ImagePod API",
        "version": __version__,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "debug": settings.debug
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
