from fastapi import FastAPI
from api.auth import router as auth_router
from contextlib import asynccontextmanager
from api.agents import router as agent_router
from api.ship import router as ship_router



import db.models

from db.engine import create_db_and_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router, prefix="/auth", tags=["auth"])

app.include_router(ship_router, prefix="/ships", tags=["ships"])

app.include_router(agent_router , prefix="/agent_ping", tags=["agent_ping"])

@app.get("/healthz")
def healthz():
    return {"status": "ok"}