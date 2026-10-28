"""Generate deterministic-looking demo data for the PostgreSQL database."""

from __future__ import annotations

import argparse
import os
import random
from datetime import date, timedelta
from typing import Any

import psycopg


SKILLS = [
    ("Python", "Programming"),
    ("PostgreSQL", "Database"),
    ("SQL", "Database"),
    ("FastAPI", "Backend"),
    ("Django", "Backend"),
    ("Power BI", "BI"),
    ("Pandas", "Data"),
    ("Docker", "DevOps"),
    ("Git", "Tools"),
    ("JavaScript", "Frontend"),
    ("React", "Frontend"),
    ("Machine Learning", "AI"),
]
LOCATIONS = ["Ha Noi", "Ho Chi Minh", "Da Nang", "Can Tho"]
JOB_TITLES = [
    "Backend Python Developer",
    "Data Analyst",
    "Full Stack Developer",
    "Database Engineer",
    "BI Developer",
    "Machine Learning Engineer",
]
APPLICATION_STATUSES = ["submitted", "screening", "interview", "offered", "rejected"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--applicants", type=int, default=100)
    parser.add_argument("--employers", type=int, default=20)
    parser.add_argument("--jobs", type=int, default=50)
    parser.add_argument("--applications", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--prefix", default="demo")
    return parser.parse_args()


def positive(value: int, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be >= 0")


def insert_user(
    cur: psycopg.Cursor[Any],
    email: str,
    full_name: str,
    role: str,
) -> int:
    cur.execute(
        """
        INSERT INTO users (email, password_hash, full_name, role)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (email, "demo-only-hash", full_name, role),
    )
    return cur.fetchone()[0]


def main() -> None:
    args = parse_args()
    for name in ("applicants", "employers", "jobs", "applications"):
        positive(getattr(args, name), name)
    if args.applications and not args.applicants:
        raise ValueError("applications requires at least one applicant")
    if args.applications and not args.jobs:
        raise ValueError("applications requires at least one job")

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres@localhost:5433/he_thong_tim_viec",
    )
    rng = random.Random(args.seed)

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cur:
            cur.execute("SELECT id, name FROM skills")
            skill_ids = {name: skill_id for skill_id, name in cur.fetchall()}
            for name, category in SKILLS:
                if name not in skill_ids:
                    cur.execute(
                        """
                        INSERT INTO skills (name, category)
                        VALUES (%s, %s)
                        RETURNING id
                        """,
                        (name, category),
                    )
                    skill_ids[name] = cur.fetchone()[0]

            applicant_ids: list[int] = []
            for index in range(1, args.applicants + 1):
                full_name = f"Demo Applicant {index:04d}"
                user_id = insert_user(
                    cur,
                    f"{args.prefix}.applicant{index:04d}@example.test",
                    full_name,
                    "applicant",
                )
                cur.execute(
                    """
                    INSERT INTO applicants
                        (user_id, phone, location, headline, summary, cv_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        f"09{index:08d}"[-10:],
                        rng.choice(LOCATIONS),
                        rng.choice(JOB_TITLES),
                        f"Generated profile for {full_name}.",
                        f"https://example.test/cv/{args.prefix}/applicant{index:04d}",
                    ),
                )
                applicant_id = cur.fetchone()[0]
                applicant_ids.append(applicant_id)
                chosen_skills = rng.sample(SKILLS, k=rng.randint(3, 6))
                for skill_name, _ in chosen_skills:
                    cur.execute(
                        """
                        INSERT INTO applicant_skills
                            (applicant_id, skill_id, proficiency_level, years_experience)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            applicant_id,
                            skill_ids[skill_name],
                            rng.randint(2, 5),
                            round(rng.uniform(0.5, 7.0), 1),
                        ),
                    )

            employer_ids: list[int] = []
            for index in range(1, args.employers + 1):
                user_id = insert_user(
                    cur,
                    f"{args.prefix}.employer{index:04d}@example.test",
                    f"Demo Employer HR {index:04d}",
                    "employer",
                )
                cur.execute(
                    """
                    INSERT INTO employers
                        (user_id, company_name, company_size, industry, website, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        f"Demo Company {index:04d}",
                        rng.choice(["11-50", "51-200", "201-500"]),
                        rng.choice(["Software", "Analytics", "Finance", "Retail"]),
                        f"https://example.test/company/{args.prefix}{index:04d}",
                        "Generated employer for testing.",
                    ),
                )
                employer_ids.append(cur.fetchone()[0])

            job_ids: list[int] = []
            for index in range(1, args.jobs + 1):
                employer_id = rng.choice(employer_ids)
                salary_min = rng.randrange(12000000, 30000001, 1000000)
                salary_max = salary_min + rng.randrange(5000000, 20000001, 1000000)
                cur.execute(
                    """
                    INSERT INTO job_postings
                        (employer_id, title, description, location, employment_type,
                         salary_min, salary_max, status, deadline)
                    VALUES (%s, %s, %s, %s, 'full-time', %s, %s, 'open', %s)
                    RETURNING id
                    """,
                    (
                        employer_id,
                        f"{rng.choice(JOB_TITLES)} {index:04d}",
                        "Generated job posting for integration and BI testing.",
                        rng.choice(LOCATIONS),
                        salary_min,
                        salary_max,
                        date.today() + timedelta(days=rng.randint(15, 90)),
                    ),
                )
                job_id = cur.fetchone()[0]
                job_ids.append(job_id)
                for skill_name, _ in rng.sample(SKILLS, k=rng.randint(3, 6)):
                    cur.execute(
                        """
                        INSERT INTO job_skills (job_id, skill_id, is_required, minimum_years)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (job_id, skill_ids[skill_name], rng.random() < 0.75, rng.randint(0, 4)),
                    )

            pairs = rng.sample(
                [(applicant_id, job_id) for applicant_id in applicant_ids for job_id in job_ids],
                k=min(args.applications, len(applicant_ids) * len(job_ids)),
            )
            for applicant_id, job_id in pairs:
                status = rng.choice(APPLICATION_STATUSES)
                cur.execute(
                    """
                    INSERT INTO applications
                        (applicant_id, job_id, status, matching_score, cover_letter)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        applicant_id,
                        job_id,
                        status,
                        round(rng.uniform(45, 99), 2),
                        "Generated application for testing.",
                    ),
                )

    print(
        f"Inserted demo data: {args.applicants} applicants, "
        f"{args.employers} employers, {args.jobs} jobs, "
        f"{len(pairs)} applications."
    )


if __name__ == "__main__":
    main()
