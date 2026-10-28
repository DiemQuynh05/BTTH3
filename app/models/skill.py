from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    applicants: Mapped[list["ApplicantSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["JobSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )


class ApplicantSkill(Base):
    __tablename__ = "applicant_skills"

    applicant_id: Mapped[int] = mapped_column(
        ForeignKey("applicants.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    proficiency_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)

    applicant: Mapped["Applicant"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(back_populates="applicants")


class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    is_required: Mapped[bool] = mapped_column(default=True, nullable=False)
    minimum_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    job: Mapped["JobPosting"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(back_populates="jobs")


from app.models.applicant import Applicant  # noqa: E402, F401
from app.models.job import JobPosting  # noqa: E402, F401

