from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.core.config import settings
from app.db import engine
from app import models  # noqa: F401
from app.routers.auth import router as auth_router

app = FastAPI(title="Laboratorio API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

health_router = APIRouter()


@health_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


app.include_router(health_router)

app.include_router(auth_router, prefix="/auth", tags=["auth"])


@app.on_event("startup")
def on_startup() -> None:
    SQLModel.metadata.create_all(engine)
