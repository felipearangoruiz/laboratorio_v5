from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.organizations import router as organizations_router
from app.routers.groups import router as groups_router
from app.routers.interview_public import router as interview_public_router
from app.routers.members import router as members_router

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

app.include_router(organizations_router, prefix="/organizations", tags=["organizations"])
app.include_router(groups_router, tags=["groups"])
app.include_router(interview_public_router, tags=["interview-public"])
app.include_router(members_router, tags=["members"])
