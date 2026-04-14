# backend/main.py - Try importing at module level
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import warnings

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Import at module level to catch errors early
from database import get_db
from models import Base
from routers import graph, pipeline, cri, ablation, compare, upload, domain, cpl_mapping

# Try to create tables
try:
    from database import engine

    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"DB init: {e}")

app = FastAPI(title="IR-KG Web API")

_origins = os.getenv("ALLOWED_ORIGINS", "https://irkg-disertasi-halim.vercel.app")
_allowed = [o.strip() for o in _origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=_allowed, allow_methods=["*"], allow_headers=["*"]
)

app.include_router(graph.router, prefix="/api/graph", tags=["KG"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["Pipeline"])
app.include_router(cri.router, prefix="/api/cri", tags=["CRI"])
app.include_router(ablation.router, prefix="/api/ablation", tags=["Ablation"])
app.include_router(compare.router, prefix="/api/compare", tags=["Compare"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(domain.router, prefix="/api/domain", tags=["Domain"])
app.include_router(cpl_mapping.router, prefix="/api/cpl-mapping", tags=["CPL"])


@app.get("/")
def root():
    return {"status": "IR-KG API v3.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
