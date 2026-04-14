# backend/main.py - Minimal Vercel
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

app = FastAPI(title="IR-KG Web API")

# CORS
_origins = os.getenv(
    "ALLOWED_ORIGINS", "https://irkg-disertasi-halim.vercel.app,http://localhost:5173"
)
allowed = [o.strip() for o in _origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=allowed, allow_methods=["*"], allow_headers=["*"]
)

try:
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

    app.include_router(graph.router, prefix="/api/graph", tags=["KG"])
    app.include_router(pipeline.router, prefix="/api/pipeline", tags=["Pipeline"])
    app.include_router(cri.router, prefix="/api/cri", tags=["CRI"])
    app.include_router(ablation.router, prefix="/api/ablation", tags=["Ablation"])
    app.include_router(compare.router, prefix="/api/compare", tags=["Compare"])
    app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
    app.include_router(domain.router, prefix="/api/domain", tags=["Domain"])
    app.include_router(cpl_mapping.router, prefix="/api/cpl-mapping", tags=["CPL"])
    print("Routers loaded OK")
except Exception as e:
    print(f"Routers error: {e}")


@app.get("/")
def root():
    return {"status": "IR-KG API v3.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
