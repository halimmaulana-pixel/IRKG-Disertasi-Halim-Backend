# backend/main.py - Working version with routers
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import warnings

warnings.filterwarnings("ignore")

# Paths
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

app = FastAPI(title="IR-KG Web API")

# CORS
_origins = os.getenv("ALLOWED_ORIGINS", "https://irkg-disertasi-halim.vercel.app")
_allowed = [o.strip() for o in _origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=_allowed, allow_methods=["*"], allow_headers=["*"]
)


# Import routers carefully
def import_routers():
    try:
        from database import get_db
        from models import Base

        try:
            from database import engine

            Base.metadata.create_all(bind=engine)
        except:
            pass

        from routers.graph import router as graph_router
        from routers.pipeline import router as pipeline_router
        from routers.cri import router as cri_router
        from routers.ablation import router as ablation_router
        from routers.compare import router as compare_router
        from routers.upload import router as upload_router
        from routers.domain import router as domain_router
        from routers.cpl_mapping import router as cpl_mapping_router

        app.include_router(graph_router, prefix="/api/graph", tags=["KG"])
        app.include_router(pipeline_router, prefix="/api/pipeline", tags=["Pipeline"])
        app.include_router(cri_router, prefix="/api/cri", tags=["CRI"])
        app.include_router(ablation_router, prefix="/api/ablation", tags=["Ablation"])
        app.include_router(compare_router, prefix="/api/compare", tags=["Compare"])
        app.include_router(upload_router, prefix="/api/upload", tags=["Upload"])
        app.include_router(domain_router, prefix="/api/domain", tags=["Domain"])
        app.include_router(cpl_mapping_router, prefix="/api/cpl-mapping", tags=["CPL"])

        return True
    except Exception as e:
        print(f"Router import error: {e}", file=sys.stderr)
        return False


# Try to load routers
loaded = import_routers()


@app.get("/")
def root():
    return {"status": "IR-KG API v3.0", "routers_loaded": loaded}


@app.get("/health")
def health():
    return {"status": "healthy"}
