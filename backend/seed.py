from __future__ import annotations

from sqlmodel import SQLModel, Session, create_engine, select

from app.core.config import settings
from app.core.security import hash_password
from app.models import Group, Organization, User, UserRole

SUPERADMIN_EMAIL = "superadmin@lab.com"
SUPERADMIN_PASSWORD = "changeme123"


def ensure_superadmin(
    session: Session,
    organization_id,
) -> User:
    superadmin = session.exec(
        select(User).where(User.email == SUPERADMIN_EMAIL)
    ).first()
    hashed_password = hash_password(SUPERADMIN_PASSWORD)

    if superadmin is None:
        superadmin = User(
            email=SUPERADMIN_EMAIL,
            hashed_password=hashed_password,
            role=UserRole.SUPERADMIN,
            organization_id=organization_id,
        )
    else:
        superadmin.hashed_password = hashed_password
        superadmin.role = UserRole.SUPERADMIN
        if superadmin.organization_id is None:
            superadmin.organization_id = organization_id

    session.add(superadmin)
    session.commit()
    session.refresh(superadmin)
    return superadmin


def seed() -> None:
    engine = create_engine(settings.DATABASE_URL)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        organization = session.exec(
            select(Organization).where(Organization.name == "Laboratorio Demo")
        ).first()

        if organization is None:
            organization = Organization(
                name="Laboratorio Demo",
                description="Organización de desarrollo local",
                sector="",
            )
            session.add(organization)
            session.commit()
            session.refresh(organization)

        default_group = session.exec(
            select(Group).where(
                Group.organization_id == organization.id,
                Group.name == "default",
            )
        ).first()

        if default_group is None:
            default_group = Group(
                organization_id=organization.id,
                name="default",
                description="Grupo por defecto",
                is_default=True,
            )
            session.add(default_group)

        superadmin = ensure_superadmin(
            session=session,
            organization_id=organization.id,
        )

        if organization.admin_id != superadmin.id:
            organization.admin_id = superadmin.id
            session.add(organization)

        session.commit()


if __name__ == "__main__":
    seed()
    print("Seed completado.")
