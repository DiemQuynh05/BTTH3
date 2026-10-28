from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Applicant(TimestampMixin, Base):
    __tablename__ = "applicants"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    phone: Mapped[str | None] = mapped_column(nullable=True)
    location: Mapped[str | None] = mapped_column(nullable=True)
    headline: Mapped[str | None] = mapped_column(nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_url: Mapped[str | None] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship(back_populates="applicant_profile")
    skills: Mapped[list["ApplicantSkill"]] = relationship(
        back_populates="applicant", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(back_populates="applicant")


from app.models.application import Application  # noqa: E402, F401
from app.models.skill import ApplicantSkill  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401

