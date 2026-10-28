from enum import StrEnum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class UserRole(StrEnum):
    APPLICANT = "applicant"
    EMPLOYER = "employer"
    ADMIN = "admin"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(150))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            values_callable=lambda roles: [role.value for role in roles],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    applicant_profile: Mapped["Applicant | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    employer_profile: Mapped["Employer | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


from app.models.applicant import Applicant  # noqa: E402, F401
from app.models.employer import Employer  # noqa: E402, F401
