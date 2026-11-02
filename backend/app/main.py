from fastapi import FastAPI
from api.auth import router as auth_router
app = FastAPI()

app.include_router(auth_router, prefix="/auth", tags=["auth"])


@app.get("/healthz")
def healthz():
    return {"status": "ok"}