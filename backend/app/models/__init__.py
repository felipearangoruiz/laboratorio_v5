from sqlmodel import SQLModel

from .analysis import (
    AnalysisRun,
    AnalysisRunCreate,
    AnalysisRunRead,
    DocumentExtraction,
    DocumentExtractionCreate,
    DocumentExtractionRead,
    EvidenceLink,
    EvidenceLinkCreate,
    EvidenceLinkRead,
    Finding,
    FindingCreate,
    FindingRead,
    GroupAnalysis,
    GroupAnalysisCreate,
    GroupAnalysisRead,
    NodeAnalysis,
    NodeAnalysisCreate,
    NodeAnalysisRead,
    OrgAnalysis,
    OrgAnalysisCreate,
    OrgAnalysisRead,
    Recommendation,
    RecommendationCreate,
    RecommendationRead,
)
from .diagnosis import DiagnosisCreate, DiagnosisResult, DiagnosisResultRead
from .document import Document, DocumentRead, DocType
from .group import Group, GroupRead
from .interview import Interview, InterviewRead
from .job import JobState, JobStatus, JobStatusRead
from .lateral_relation import (
    LateralRelation,
    LateralRelationCreate,
    LateralRelationRead,
)
from .member import Member, MemberRead, MemberTokenStatus
from .membership import Membership, MembershipRead
from .organization import (
    Organization,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from .processing import ProcessingResult, ProcessingResultRead, ProcessingType
from .quick_assessment import (
    DimensionScoreRead,
    InviteMember,
    InviteMembersRequest,
    MemberRespondRequest,
    QuickAssessment,
    QuickAssessmentCreate,
    QuickAssessmentMember,
    QuickAssessmentMemberCreate,
    QuickAssessmentMemberRead,
    QuickAssessmentRead,
    QuickAssessmentScoreRead,
    QuickAssessmentStatus,
)
from .user import User, UserRead, UserRole

__all__ = [
    "SQLModel",
    # Motor de análisis (pipeline 4 pasos)
    "AnalysisRun",
    "AnalysisRunCreate",
    "AnalysisRunRead",
    "NodeAnalysis",
    "NodeAnalysisCreate",
    "NodeAnalysisRead",
    "GroupAnalysis",
    "GroupAnalysisCreate",
    "GroupAnalysisRead",
    "OrgAnalysis",
    "OrgAnalysisCreate",
    "OrgAnalysisRead",
    "DocumentExtraction",
    "DocumentExtractionCreate",
    "DocumentExtractionRead",
    "Finding",
    "FindingCreate",
    "FindingRead",
    "Recommendation",
    "RecommendationCreate",
    "RecommendationRead",
    "EvidenceLink",
    "EvidenceLinkCreate",
    "EvidenceLinkRead",
    # User
    "User",
    "UserRead",
    "UserRole",
    # Organization
    "Organization",
    "OrganizationCreate",
    "OrganizationRead",
    "OrganizationUpdate",
    # Document (institutional files)
    "Document",
    "DocumentRead",
    "DocType",
    # Group (canvas node)
    "Group",
    "GroupRead",
    # Member
    "Member",
    "MemberRead",
    "MemberTokenStatus",
    # Interview
    "Interview",
    "InterviewRead",
    # Lateral relation (canvas horizontal edges)
    "LateralRelation",
    "LateralRelationCreate",
    "LateralRelationRead",
    # Membership (user ↔ org with role)
    "Membership",
    "MembershipRead",
    # Diagnosis (external Codex processor result)
    "DiagnosisResult",
    "DiagnosisResultRead",
    "DiagnosisCreate",
    # Legacy processing + jobs
    "ProcessingResult",
    "ProcessingResultRead",
    "ProcessingType",
    "JobStatus",
    "JobStatusRead",
    "JobState",
    # Quick assessment (free flow)
    "QuickAssessment",
    "QuickAssessmentCreate",
    "QuickAssessmentRead",
    "QuickAssessmentStatus",
    "QuickAssessmentScoreRead",
    "QuickAssessmentMember",
    "QuickAssessmentMemberCreate",
    "QuickAssessmentMemberRead",
    "DimensionScoreRead",
    "InviteMember",
    "InviteMembersRequest",
    "MemberRespondRequest",
]
