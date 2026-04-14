# Simple test
from fastapi import FastAPI, APIRouter

app = FastAPI()

# Try importing routers
try:
    import routers.graph

    router = APIRouter()

    @router.get("/test")
    def test():
        return {"ok": True}

    app.include_router(router, prefix="/api/graph")
    print("Router loaded")
except Exception as e:
    print(f"Error: {e}")


@app.get("/")
def root():
    return {"status": "OK"}


@app.get("/health")
def health():
    return {"status": "healthy"}
