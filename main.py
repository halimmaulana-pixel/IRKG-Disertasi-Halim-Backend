# backend/main.py - Dynamic import approach
import os, sys, importlib
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

app = FastAPI(title="IR-KG Web API")

_origins = os.getenv("ALLOWED_ORIGINS", "https://irkg-disertasi-halim.vercel.app")
_allowed = [o.strip() for o in _origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=_allowed, allow_methods=["*"], allow_headers=["*"]
)

# Try loading each router with try-except
for router_name in [
    "graph",
    "pipeline",
    "cri",
    "ablation",
    "compare",
    "upload",
    "domain",
    "cpl_mapping",
]:
    try:
        module = importlib.import_module(f"routers.{router_name}")
        router = getattr(module, "router", None)
        if router:
            app.include_router(
                router, prefix=f"/api/{router_name}", tags=[router_name.title()]
            )
            print(f"Loaded {router_name}")
    except Exception as e:
        print(f"Failed {router_name}: {e}", file=sys.stderr)


@app.get("/")
def root():
    return {"status": "IR-KG API v3.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
