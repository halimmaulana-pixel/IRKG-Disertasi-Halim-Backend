# Simple working test
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"status": "OK", "message": "Backend working!"}


@app.get("/health")
def health():
    return {"status": "healthy"}
