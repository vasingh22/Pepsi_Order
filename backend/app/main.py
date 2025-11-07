"""
Main FastAPI application for Pepsi Order Digitization System
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.api.routes import upload, status, results, corrections, metrics
from app.api.routes import process as process_route
from app.database.database import engine, Base
from app.core.config import settings

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    print("🚀 Starting Pepsi Order Digitization API...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"✅ Upload directory ready: {settings.UPLOAD_DIR}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Automated document processing system for PepsiCo order digitization",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(status.router, prefix="/api", tags=["Status"])
app.include_router(results.router, prefix="/api", tags=["Results"])
app.include_router(corrections.router, prefix="/api", tags=["Corrections"])
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])
app.include_router(process_route.router, prefix="/api", tags=["Process"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Pepsi Order Digitization API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "pepsi-order-api"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

