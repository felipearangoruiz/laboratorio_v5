"""Capa Recolección — invitations from canvas nodes, reminders, revocation, threshold."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, func, select

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.group import Group
from app.models.interview import Interview
from app.models.member import Member, MemberTokenStatus
from app.models.user import User, UserRole
from app.questions_instrument_v2 import (
    EMPLOYEE_SECTIONS,
    MANAGER_SECTIONS,
    ADAPTIVE_QUESTIONS,
    HYPOTHESIS_RULES,
    QUESTION_BY_ID,
)

router = APIRouter()

THRESHOLD_PERCENT = 0.40
THRESHOLD_MIN_INTERVIEWS = 5
MAX_REMINDERS = 3


def _can_access_org(user: User, org_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == org_id


# ── Invite a member from a canvas node ──────────────────

class InviteFromNodeRequest(BaseModel):
    name: str
    role_label: str = ""


@router.post("/organizations/{org_id}/nodes/{node_id}/invite", status_code=201)
def invite_from_node(
    org_id: UUID,
    node_id: UUID,
    body: InviteFromNodeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> dict:
    """Invite a member from a canvas node.

    The email is read from the node's saved email field (set in the Estructura layer).
    If the node has no email assigned, returns 400 — the admin must assign it first.
    """
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    group = session.get(Group, node_id)
    if not group or group.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Node not found")

    # Email must be set on the node (assigned in Estructura layer)
    if not group.email or not group.email.strip():
        raise HTTPException(
            status_code=400,
            detail="Este nodo no tiene email asignado. Asígnalo en la capa Estructura.",
        )

    node_email = group.email.strip()

    # Prevent duplicate invite for the same node
    existing = session.exec(
        select(Member).where(
            Member.organization_id == org_id,
            Member.group_id == node_id,
        )
    ).first()
    if existing:
        # Return the existing member's token instead of creating a duplicate
        interview_link = f"{settings.FRONTEND_URL}/interview/{existing.interview_token}"
        return {
            "member_id": str(existing.id),
            "token": existing.interview_token,
            "interview_link": interview_link,
            "status": existing.token_status.value,
            "email": node_email,
        }

    member = Member(
        organization_id=org_id,
        group_id=node_id,
        name=body.name,
        role_label=body.role_label,
    )
    session.add(member)
    session.commit()
    session.refresh(member)

    interview_link = f"{settings.FRONTEND_URL}/interview/{member.interview_token}"

    return {
        "member_id": str(member.id),
        "token": member.interview_token,
        "interview_link": interview_link,
        "status": member.token_status.value,
        "email": node_email,
    }


# ── Reminder ────────────────────────────────────────────

@router.post("/members/{member_id}/remind")
def send_reminder(
    member_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> dict:
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if not _can_access_org(current_user, member.organization_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    if member.token_status == MemberTokenStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Interview already completed")
    if member.token_status == MemberTokenStatus.EXPIRED:
        raise HTTPException(status_code=400, detail="Invitation expired")

    # Track reminders in interview data or a simple counter
    interview = session.exec(
        select(Interview).where(Interview.member_id == member_id)
    ).first()

    reminder_count = 0
    if interview and interview.data:
        reminder_count = interview.data.get("_reminder_count", 0)

    if reminder_count >= MAX_REMINDERS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_REMINDERS} reminders reached")

    # Increment reminder count
    if interview:
        interview.data = {**interview.data, "_reminder_count": reminder_count + 1}
        session.add(interview)
    else:
        interview = Interview(
            member_id=member.id,
            organization_id=member.organization_id,
            group_id=member.group_id,
            data={"_reminder_count": 1},
            submitted_at=None,
        )
        session.add(interview)

    session.commit()

    # TODO: integrate email service to actually send reminder
    return {"status": "reminder_sent", "reminder_count": reminder_count + 1}


# ── Revoke invitation ───────────────────────────────────

@router.post("/members/{member_id}/revoke")
def revoke_invitation(
    member_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> dict:
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if not _can_access_org(current_user, member.organization_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    member.token_status = MemberTokenStatus.EXPIRED
    session.add(member)
    session.commit()

    return {"status": "revoked"}


# ── Collection status for canvas ────────────────────────

@router.get("/organizations/{org_id}/collection/status")
def collection_status(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> dict:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Count nodes (groups)
    total_nodes = session.exec(
        select(func.count(Group.id)).where(Group.organization_id == org_id)
    ).one()

    # Count members by status
    members = session.exec(
        select(Member).where(Member.organization_id == org_id)
    ).all()

    total_members = len(members)
    by_status = {
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
        "expired": 0,
    }
    for m in members:
        by_status[m.token_status.value] += 1

    completed = by_status["completed"]

    # Nodes with completed interviews
    nodes_with_interview = session.exec(
        select(func.count(func.distinct(Member.group_id))).where(
            Member.organization_id == org_id,
            Member.token_status == MemberTokenStatus.COMPLETED,
            Member.group_id.is_not(None),
        )
    ).one()

    # Threshold calculation
    threshold_percent = (nodes_with_interview / total_nodes * 100) if total_nodes > 0 else 0
    threshold_met = (
        threshold_percent >= THRESHOLD_PERCENT * 100
        and completed >= THRESHOLD_MIN_INTERVIEWS
    )

    # Per-node interview status (highest-priority status wins)
    # Priority: completed > in_progress > pending > expired > none
    STATUS_PRIORITY: dict[str, int] = {
        "completed": 4,
        "in_progress": 3,
        "pending": 2,
        "expired": 1,
    }
    node_statuses: dict[str, str] = {}
    for m in members:
        if m.group_id is None:
            continue
        node_id_str = str(m.group_id)
        current_priority = STATUS_PRIORITY.get(node_statuses.get(node_id_str, ""), 0)
        new_priority = STATUS_PRIORITY.get(m.token_status.value, 0)
        if new_priority > current_priority:
            node_statuses[node_id_str] = m.token_status.value

    return {
        "total_nodes": total_nodes,
        "total_members": total_members,
        "by_status": by_status,
        "completed": completed,
        "nodes_with_interview": nodes_with_interview,
        "threshold_percent": round(threshold_percent, 1),
        "threshold_met": threshold_met,
        "node_statuses": node_statuses,
    }


# ── Node interview details (for side panel) ─────────────

@router.get("/organizations/{org_id}/nodes/{node_id}/interviews")
def node_interview_details(
    org_id: UUID,
    node_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[dict]:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    members = session.exec(
        select(Member).where(
            Member.organization_id == org_id,
            Member.group_id == node_id,
        )
    ).all()

    result = []
    for m in members:
        interview = session.exec(
            select(Interview).where(Interview.member_id == m.id)
        ).first()

        reminder_count = 0
        if interview and interview.data:
            reminder_count = interview.data.get("_reminder_count", 0)

        result.append({
            "member_id": str(m.id),
            "name": m.name,
            "role_label": m.role_label,
            "interview_token": m.interview_token,
            "token_status": m.token_status.value,
            "submitted_at": interview.submitted_at.isoformat() if interview and interview.submitted_at else None,
            "reminder_count": reminder_count,
        })

    return result


# ── Instrument v2 questions endpoints ─────────────────────

@router.get("/interview/premium/questions")
def get_premium_questions() -> dict:
    """Public endpoint — returns the v2 instrument question bank."""
    return {
        "version": 2,
        "manager_sections": MANAGER_SECTIONS,
        "employee_sections": EMPLOYEE_SECTIONS,
        "adaptive_questions": ADAPTIVE_QUESTIONS,
        "hypothesis_rules": HYPOTHESIS_RULES,
    }
