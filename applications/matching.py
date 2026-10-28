from decimal import Decimal


def calculate_matching_score(candidate, job):
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
