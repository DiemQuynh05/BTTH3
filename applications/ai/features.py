import re
from dataclasses import dataclass, field

import numpy as np

from .text import normalize_text

FEATURE_NAMES = (
    "required_skill_coverage",
    "preferred_skill_coverage",
    "skill_overlap",
    "text_similarity",
    "title_similarity",
    "experience_gap",
    "meets_experience",
    "education_gap",
    "location_fit",
    "salary_fit",
)
FEATURE_LABELS = {
    "required_skill_coverage": "Kỹ năng bắt buộc",
    "preferred_skill_coverage": "Kỹ năng ưu tiên",
    "skill_overlap": "Độ trùng khớp kỹ năng",
    "text_similarity": "Tương đồng nội dung CV - JD",
    "title_similarity": "Tương đồng chuyên ngành/chức danh",
    "experience_gap": "Chênh lệch kinh nghiệm",
    "meets_experience": "Đạt yêu cầu kinh nghiệm",
    "education_gap": "Trình độ học vấn",
    "location_fit": "Địa điểm làm việc",
    "salary_fit": "Mức lương mong muốn",
}
LEVEL_MIN_YEARS = {"ENTRY": 0.0, "JUNIOR": 1.0, "MID": 3.0, "SENIOR": 5.0}
CITY_ALIASES = {
    "ho chi minh": ("ho chi minh", "hcm", "sai gon", "saigon"),
    "ha noi": ("ha noi", "hanoi"),
    "da nang": ("da nang", "danang"),
    "can tho": ("can tho",),
    "hai phong": ("hai phong",),
    "binh duong": ("binh duong",),
    "dong nai": ("dong nai", "bien hoa"),
}


@dataclass
class CandidateDoc:
    text: str = ""
    title: str = ""
    skills: set = field(default_factory=set)
    experience_years: float = 0.0
    education_level: int = 0
    location: str = ""
    desired_salary: float | None = None


@dataclass
class JobDoc:
    text: str = ""
    title: str = ""
    required_skills: set = field(default_factory=set)
    preferred_skills: set = field(default_factory=set)
    min_years: float = 0.0
    education_level: int = 0
    location: str = ""
    work_mode: str = "ONSITE"
    salary_min: float | None = None
    salary_max: float | None = None


def detect_city(location):
    normalized = normalize_text(location)
    for city, aliases in CITY_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases):
            return city
    return normalized or None


def location_fit(candidate, job):
    if job.work_mode == "REMOTE":
        return 1.0
    candidate_city, job_city = detect_city(candidate.location), detect_city(job.location)
    if not candidate_city or not job_city:
        return 0.5
    if candidate_city == job_city:
        return 1.0
    return 0.5 if job.work_mode == "HYBRID" else 0.0


def salary_fit(candidate, job):
    if not candidate.desired_salary or not job.salary_max:
        return 0.5
    if candidate.desired_salary <= job.salary_max:
        return 1.0
    return max(0.0, 1 - (candidate.desired_salary - job.salary_max) / job.salary_max)


def structured_features(candidate, job):
    skills = candidate.skills
    required, preferred = job.required_skills, job.preferred_skills
    job_skills = required | preferred
    union = skills | job_skills
    education_gap = 0.0
    if candidate.education_level and job.education_level:
        education_gap = float(np.clip(candidate.education_level - job.education_level, -2, 2) / 2)
    return {
        "required_skill_coverage": len(skills & required) / len(required) if required else 1.0,
        "preferred_skill_coverage": len(skills & preferred) / len(preferred) if preferred else 1.0,
        "skill_overlap": len(skills & job_skills) / len(union) if union else 0.0,
        "experience_gap": float(np.clip(candidate.experience_years - job.min_years, -5, 5) / 5),
        "meets_experience": 1.0 if candidate.experience_years >= job.min_years else 0.0,
        "education_gap": education_gap,
        "location_fit": location_fit(candidate, job),
        "salary_fit": salary_fit(candidate, job),
    }


def _row_cosine(vectorizer, left, right):
    # TfidfVectorizer chuẩn hóa L2 nên tích vô hướng từng dòng chính là cosine similarity.
    left_matrix, right_matrix = vectorizer.transform(left), vectorizer.transform(right)
    return np.asarray(left_matrix.multiply(right_matrix).sum(axis=1)).ravel()


def feature_matrix(candidates, jobs, vectorizer):
    text_similarity = _row_cosine(vectorizer, [c.text for c in candidates], [j.text for j in jobs])
    title_similarity = _row_cosine(vectorizer, [c.title for c in candidates], [j.title for j in jobs])
    rows = []
    for index, (candidate, job) in enumerate(zip(candidates, jobs)):
        values = structured_features(candidate, job)
        values["text_similarity"] = text_similarity[index]
        values["title_similarity"] = title_similarity[index]
        rows.append([values[name] for name in FEATURE_NAMES])
    return np.asarray(rows, dtype=float).reshape(len(rows), len(FEATURE_NAMES))
