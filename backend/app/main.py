from fastapi import FastAPI
from api.auth import router as auth_router

from api.order import router as order_router
from api.ship import router as ship_router

app = FastAPI()

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(order_router, prefix="/orders", tags=["orders"])
app.include_router(ship_router, prefix="/ships", tags=["ships"])


@app.get("/healthz")
def healthz():
    return {"status": "ok"}