# backend/main.py
import os, sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add paths
CURRENT_DIR = Path(__file__).parent
sys.path.insert(0, str(CURRENT_DIR))

# Force explicit imports
import routers.graph
import routers.pipeline
import routers.cri
import routers.ablation
import routers.compare
import routers.upload
import routers.domain
import routers.cpl_mapping
import database
import models

print(f"Loaded routers: graph={hasattr(routers, 'graph')}", file=sys.stderr)

app = FastAPI(title="IR-KG Web API")

_origins = os.getenv("ALLOWED_ORIGINS", "https://irkg-disertasi-halim.vercel.app")
_allowed = [o.strip() for o in _origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=_allowed, allow_methods=["*"], allow_headers=["*"]
)

app.include_router(routers.graph.router, prefix="/api/graph", tags=["KG"])
app.include_router(routers.pipeline.router, prefix="/api/pipeline", tags=["Pipeline"])
app.include_router(routers.cri.router, prefix="/api/cri", tags=["CRI"])
app.include_router(routers.ablation.router, prefix="/api/ablation", tags=["Ablation"])
app.include_router(routers.compare.router, prefix="/api/compare", tags=["Compare"])
app.include_router(routers.upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(routers.domain.router, prefix="/api/domain", tags=["Domain"])
app.include_router(routers.cpl_mapping.router, prefix="/api/cpl-mapping", tags=["CPL"])


@app.get("/")
def root():
    return {"status": "IR-KG API v3.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
