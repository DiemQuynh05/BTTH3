from enum import StrEnum
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ApplicationStatus(StrEnum):
    SUBMITTED = "submitted"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFERED = "offered"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("applicant_id", "job_id", name="uq_application_applicant_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("applicants.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id", ondelete="CASCADE"))
    status: Mapped[ApplicationStatus] = mapped_column(default=ApplicationStatus.SUBMITTED)
    matching_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)

    applicant: Mapped["Applicant"] = relationship(back_populates="applications")
    job: Mapped["JobPosting"] = relationship(back_populates="applications")


from app.models.applicant import Applicant  # noqa: E402, F401
from app.models.job import JobPosting  # noqa: E402, F401

