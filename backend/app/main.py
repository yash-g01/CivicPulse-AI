from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.mock_portal import mock_router

from app.config import settings

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

app = FastAPI(
    title="CivicPulse AI API",
    description="Autonomous Civic Waste Action & Ghost-Resolution Auditor Engine",
    version="1.0.0"
)

# Parse CORS Origins from environment settings
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if not cors_origins or "*" in cors_origins:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """Health check endpoint for AWS Application Load Balancers, ECS & App Runner."""
    return {
        "status": "healthy",
        "service": "CivicPulse AI API",
        "version": "1.0.0",
        "portal_mode": settings.PORTAL_MODE,
        "region": settings.AWS_REGION,
    }

@app.get("/")
def root():
    """Root endpoint for quick API discovery."""
    return {
        "name": "CivicPulse AI API",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
    }

app.include_router(router, prefix="/api/v1")
app.include_router(mock_router)