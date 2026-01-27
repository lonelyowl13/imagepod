from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
from app.config import settings
from app.database import engine, Base
from app.api import auth, jobs, endpoints, templates
from app.database import get_db
from sqlalchemy.orm import Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting ImagePod backend...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created")
    
    # Start background tasks
    # In production, you'd want to use a proper task queue like Celery
    # For now, we'll just print that we're ready
    print("ImagePod backend is ready!")
    
    yield
    
    # Shutdown
    print("Shutting down ImagePod backend...")


# Create FastAPI app
app = FastAPI(
    title="ImagePod API",
    description="RunPod clone backend service for AI/ML job processing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
    )

# Include API routers
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(endpoints.router)
app.include_router(templates.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ImagePod API",
        "version": "1.0.0",
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


@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint (for Prometheus)"""
    # In production, you'd want to use prometheus_client
    return {
        "status": "ok",
        "message": "Metrics endpoint - implement with prometheus_client"
    }


# RunPod serverless compatibility endpoints
@app.post("/runsync")
async def run_sync():
    """RunPod serverless sync endpoint compatibility"""
    return {"message": "Use /jobs/ endpoint for job creation"}


@app.post("/run")
async def run_async():
    """RunPod serverless async endpoint compatibility"""
    return {"message": "Use /jobs/ endpoint for job creation"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
