from __future__ import annotations

from sqlmodel import SQLModel, Session, create_engine, select

from app.core.config import settings
from app.core.security import hash_password
from app.models import Group, Organization, User, UserRole


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

        superadmin = session.exec(
            select(User).where(User.email == "superadmin@lab.com")
        ).first()

        if superadmin is None:
            superadmin = User(
                email="superadmin@lab.com",
                hashed_password=hash_password("changeme123"),
                role=UserRole.SUPERADMIN,
                organization_id=organization.id,
            )
            session.add(superadmin)
            session.commit()
            session.refresh(superadmin)
        elif not superadmin.hashed_password.startswith("$2"):
            superadmin.hashed_password = hash_password("changeme123")
            superadmin.role = UserRole.SUPERADMIN
            session.add(superadmin)

        if organization.admin_id != superadmin.id:
            organization.admin_id = superadmin.id
            session.add(organization)

        session.commit()


if __name__ == "__main__":
    seed()
    print("Seed completado.")
