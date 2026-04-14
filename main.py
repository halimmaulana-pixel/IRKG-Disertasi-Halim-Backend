# Simple test
from fastapi import FastAPI, APIRouter

app = FastAPI()

# Without try-except to see error
import routers.graph

router = APIRouter()


@router.get("/test")
def test():
    return {"ok": True}


app.include_router(router, prefix="/api/graph")


@app.get("/")
def root():
    return {"status": "OK"}


@app.get("/health")
def health():
    return {"status": "healthy"}
