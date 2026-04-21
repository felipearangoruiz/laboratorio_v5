from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.analysis import router as analysis_router
from app.routers.auth import router as auth_router
from app.routers.campaigns import router as campaigns_router
from app.routers.canvas import router as canvas_router
from app.routers.collection import router as collection_router
from app.routers.diagnosis import router as diagnosis_router
from app.routers.documents import router as documents_router
from app.routers.edges import router as edges_router
from app.routers.groups import router as groups_router
from app.routers.interview_public import router as interview_public_router
from app.routers.interviews import router as interviews_router
from app.routers.members import router as members_router
from app.routers.node_states import router as node_states_router
from app.routers.nodes import router as nodes_router
from app.routers.organizations import router as organizations_router
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

# Core resources
app.include_router(organizations_router, prefix="/organizations", tags=["organizations"])
app.include_router(groups_router, tags=["groups"])
app.include_router(members_router, tags=["members"])
app.include_router(interviews_router, tags=["interviews"])
app.include_router(interview_public_router, tags=["interview-public"])
app.include_router(results_router, tags=["results"])

# Sprint 1.3 — Node+Edge refactor (modelo unificado)
app.include_router(nodes_router, tags=["nodes"])
app.include_router(edges_router, tags=["edges"])
app.include_router(campaigns_router, tags=["campaigns"])
app.include_router(node_states_router, tags=["node-states"])

# Canvas (templates, CSV import) — rutas absolutas dentro del router
app.include_router(canvas_router, tags=["canvas"])

# Capa Recolección (invitaciones desde nodos, umbrales, recordatorios)
app.include_router(collection_router, tags=["collection"])

# Documentos institucionales
app.include_router(documents_router, tags=["documents"])

# Motor de diagnóstico IA (legacy — Codex externo)
app.include_router(diagnosis_router, tags=["diagnosis"])

# Motor de análisis — pipeline de 4 pasos
app.include_router(analysis_router, tags=["analysis"])

# Flujo Free (quick assessment) — prefix necesario para que coincida con el
# API client del frontend, que llama /api/quick-assessment/...
app.include_router(
    quick_assessment_router,
    prefix="/api/quick-assessment",
    tags=["quick-assessment"],
)
