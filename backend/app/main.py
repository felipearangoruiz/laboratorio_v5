from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.organizations import router as organizations_router
from app.routers.groups import router as groups_router
from app.routers.interviews import router as interviews_router
from app.routers.interview_public import router as interview_public_router
from app.routers.members import router as members_router
from app.routers.canvas import router as canvas_router
from app.routers.collection import router as collection_router
from app.routers.diagnosis import router as diagnosis_router
from app.routers.quick_assessment import router as quick_assessment_router
from app.routers.results import router as results_router

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
app.include_router(interviews_router, tags=["interviews"])
app.include_router(interview_public_router, tags=["interview-public"])
app.include_router(members_router, tags=["members"])
app.include_router(results_router, tags=["results"])
app.include_router(canvas_router, tags=["canvas"])
app.include_router(collection_router, tags=["collection"])
app.include_router(diagnosis_router, tags=["diagnosis"])
app.include_router(quick_assessment_router, prefix="/api/quick-assessment", tags=["quick-assessment"])
