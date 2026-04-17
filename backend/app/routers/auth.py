from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from pydantic import BaseModel, EmailStr

from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password, verify_token
from app.db import get_session
from app.models.organization import Organization
from app.models.user import User, UserRead, UserRole

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""
    org_name: str = ""


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    session: Session = Depends(get_session),
) -> dict:
    existing = session.exec(select(User).where(User.email == body.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create Organization first
    org = Organization(
        name=body.org_name or f"Org de {body.name or body.email}",
        description="",
        sector="",
    )
    session.add(org)
    session.flush()  # Get org.id

    # Create User linked to the Organization
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        role=UserRole.ADMIN,
        organization_id=org.id,
    )
    session.add(user)
    session.flush()

    # Link org back to user as admin
    org.admin_id = user.id
    session.add(org)
    session.commit()
    session.refresh(user)

    return {
        "id": str(user.id),
        "email": user.email,
        "organization_id": str(org.id),
    }


@router.post("/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "user_id": str(user.id),
            "role": user.role.value,
            "organization_id": str(user.organization_id) if user.organization_id else None,
        }
    )
    refresh_token = create_access_token(
        data={"sub": str(user.id), "type": "refresh"},
        expires_delta=timedelta(days=7),
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="strict",
        secure=False,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh")
def refresh_access_token(request: Request) -> dict[str, str]:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    payload = verify_token(refresh_token)
    if payload.get("type") != "refresh" or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    access_token = create_access_token(data={"sub": payload["sub"]})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key="refresh_token")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
