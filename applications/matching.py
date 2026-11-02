import logging
from decimal import Decimal
from pathlib import Path

from django.conf import settings

from .ai.cv_parser import parse_education_level, parse_resume_text
from .ai.features import LEVEL_MIN_YEARS, CandidateDoc, JobDoc
from .ai.skills import get_extractor

logger = logging.getLogger(__name__)
_MODEL_CACHE = {}
MODEL_LABELS = {"logistic_regression": "Logistic Regression", "hist_gradient_boosting": "Gradient Boosting"}


def skill_extractor():
    from jobs.models import Skill

    return get_extractor(tuple(sorted(Skill.objects.values_list("name", flat=True))))


def load_matching_model():
    """Tải mô hình đã huấn luyện (cache theo thời điểm sửa file); trả về None nếu chưa huấn luyện."""
    path = Path(settings.MATCHING_MODEL_PATH)
    try:
        modified = path.stat().st_mtime
    except OSError:
        return None
    cached = _MODEL_CACHE.get(path)
    if cached and cached[0] == modified:
        return cached[1]
    try:
        from .ai.model import MatchingModel

        model = MatchingModel.load(path)
    except Exception:
        logger.exception("Cannot load matching model from %s", path)
        model = None
    _MODEL_CACHE[path] = (modified, model)
    return model


def matching_method_label():
    model = load_matching_model()
    if model is None:
        return "Rule-based Matching"
    return f"AI Matching · {MODEL_LABELS.get(model.metadata['model_name'], model.metadata['model_name'])}"


def candidate_document(candidate, resume=None, extractor=None):
    extractor = extractor or skill_extractor()
    if resume is None:
        resume = candidate.resumes.order_by("-uploaded_at").first()
    profile_text = "\n".join(filter(None, [candidate.major, candidate.education, candidate.bio, candidate.projects]))
    text = "\n".join(filter(None, [resume.resume_text if resume else "", profile_text]))
    parsed = parse_resume_text(text, extractor=extractor)
    declared = {extractor.key(item.skill.name) for item in candidate.candidate_skills.select_related("skill")}
    return CandidateDoc(
        text=text,
        title=candidate.major,
        skills=extractor.expand(declared) | parsed.skills,
        experience_years=max(float(candidate.experience_years or 0), parsed.experience_years or 0.0),
        education_level=parsed.education_level,
        location=candidate.location,
        desired_salary=float(candidate.desired_salary) if candidate.desired_salary else None,
    )


def job_document(job, extractor=None):
    extractor = extractor or skill_extractor()
    job_skills = list(job.job_skills.select_related("skill"))
    required = {extractor.key(item.skill.name) for item in job_skills if item.importance == "REQUIRED"}
    preferred = {extractor.key(item.skill.name) for item in job_skills if item.importance == "PREFERRED"}
    text = "\n".join(filter(None, [job.title, job.description, job.requirements, job.responsibilities]))
    if not job_skills:
        # Tin chưa khai báo kỹ năng: dùng kỹ năng trích xuất từ nội dung JD làm yêu cầu.
        required = extractor.extract(text, expand=False)
    required_years = [float(item.minimum_years) for item in job_skills if item.importance == "REQUIRED"]
    return JobDoc(
        text=text,
        title=job.title,
        required_skills=required,
        preferred_skills=preferred - required,
        min_years=max([LEVEL_MIN_YEARS.get(job.experience_level, 0.0), *required_years]),
        education_level=parse_education_level(job.education_level, mode="min"),
        location=job.location,
        work_mode=job.work_mode,
        salary_min=float(job.salary_min) if job.salary_min is not None else None,
        salary_max=float(job.salary_max) if job.salary_max is not None else None,
    )


def calculate_matching_score(candidate, job, resume=None):
    """Điểm tương thích 0-100: dùng mô hình ML nếu đã huấn luyện, ngược lại dùng rule-based."""
    model = load_matching_model()
    if model is not None:
        try:
            extractor = skill_extractor()
            result = model.score(candidate_document(candidate, resume, extractor), job_document(job, extractor), extractor)
            return Decimal(str(result.score)), result.explanation
        except Exception:
            logger.exception("ML matching failed, falling back to rule-based score")
    return calculate_rule_based_score(candidate, job)


def rescore_applications(applications):
    count = 0
    for application in applications.select_related("candidate", "job", "resume"):
        application.matching_score, application.matching_explanation = calculate_matching_score(
            application.candidate, application.job, application.resume
        )
        application.save(update_fields=["matching_score", "matching_explanation"])
        count += 1
    return count


def calculate_rule_based_score(candidate, job):
    """Rule-based matching, not a machine-learning prediction."""
    candidate_skills = {
        item.skill_id: item
        for item in candidate.candidate_skills.select_related("skill")
    }
    required = list(job.job_skills.filter(importance="REQUIRED"))
    preferred = list(job.job_skills.filter(importance="PREFERRED"))
    required_hits = sum(item.skill_id in candidate_skills for item in required)
    preferred_hits = sum(item.skill_id in candidate_skills for item in preferred)
    required_score = (required_hits / len(required) * 55) if required else 55
    preferred_score = (preferred_hits / len(preferred) * 20) if preferred else 20
    experience_score = min(float(candidate.experience_years / 3), 1) * 15 if job.experience_level != "ENTRY" else 15
    salary_score = 5
    if candidate.desired_salary and job.salary_min and job.salary_max:
        salary_score = 5 if job.salary_min <= candidate.desired_salary <= job.salary_max else 2
    location_score = 5 if job.work_mode in {"REMOTE", "HYBRID"} or candidate.location == job.location else 2
    score = min(100, round(required_score + preferred_score + experience_score + salary_score + location_score, 2))
    return Decimal(str(score)), {
        "method": "rule_based",
        "required_skills": f"{required_hits}/{len(required)}",
        "preferred_skills": f"{preferred_hits}/{len(preferred)}",
        "experience": round(experience_score, 2),
        "salary": salary_score,
        "location": location_score,
    }
