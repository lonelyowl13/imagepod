from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
from app.config import settings
from app.database import engine, Base
from app.api import auth, jobs, endpoints, templates, executors


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""

    print("Starting ImagePod backend...")

    Base.metadata.create_all(bind=engine)
    print("Database tables created")

    print("ImagePod backend is ready!")
    
    yield
    
    Base.metadata.drop_all(bind=engine)
    print("Database tables nuked")
    print("Shutting down ImagePod backend...")


app = FastAPI(
    title="ImagePod API",
    description="Runpod-esque backend to run random stuff on your friend's gpu",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )


app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(endpoints.router)
app.include_router(templates.router)
app.include_router(executors.router)


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


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
