from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="AI Supply Chain Optimizer")


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}
