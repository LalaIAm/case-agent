"""
FastAPI application entry point for Minnesota Conciliation Court Case Agent.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings

app = FastAPI(title="Minnesota Conciliation Court Case Agent")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URL.split(",") if settings.FRONTEND_URL else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy"}


@app.get("/")
def root():
    """Root endpoint returning API information."""
    return {
        "name": "Minnesota Conciliation Court Case Agent",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# Future route imports (Phase 2+):
# from auth import router as auth_router
# from . import cases  # case routes
# from agents import router as agents_router
# from memory import router as memory_router
# app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
# app.include_router(cases_router, prefix="/api/cases", tags=["cases"])
# app.include_router(agents_router, prefix="/api/agents", tags=["agents"])
# app.include_router(memory_router, prefix="/api/memory", tags=["memory"])
