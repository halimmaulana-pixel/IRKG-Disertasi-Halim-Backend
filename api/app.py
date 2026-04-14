# api/app.py - Vercel Serverless Function entry point
# This file must expose a variable named 'app' for Vercel to detect FastAPI

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers - use try/except to handle missing modules gracefully
try:
    from backend.routers import (
        graph,
        pipeline,
        cri,
        ablation,
        compare,
        upload,
        domain,
        cpl_mapping,
    )
except ImportError:
    from routers import (
        graph,
        pipeline,
        cri,
        ablation,
        compare,
        upload,
        domain,
        cpl_mapping,
    )

# Import database
try:
    from backend.database import engine, get_db
    from backend.models import Base
except ImportError:
    from database import engine, get_db
    from models import Base

# Create tables if using SQLite (for Vercel with ephemeral filesystem)
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass  # Table creation may fail on first cold start, that's OK

app = FastAPI(title="IR-KG Web API", version="3.0")

# CORS - allow both production frontend and localhost
_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,https://irkg-disertasi-halim.vercel.app"
)
allowed_origins = [o.strip() for o in _origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(graph.router, prefix="/api/graph", tags=["Knowledge Graph"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["Pipeline Trace"])
app.include_router(cri.router, prefix="/api/cri", tags=["CRI Dashboard"])
app.include_router(ablation.router, prefix="/api/ablation", tags=["Ablation Study"])
app.include_router(compare.router, prefix="/api/compare", tags=["Comparison"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload CPL"])
app.include_router(domain.router, prefix="/api/domain", tags=["Domain Map"])
app.include_router(cpl_mapping.router, prefix="/api/cpl-mapping", tags=["CPL Mapping"])


@app.get("/")
def root():
    return {"status": "IR-KG API v3.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}
