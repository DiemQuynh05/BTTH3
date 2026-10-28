from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField
from django.shortcuts import render

from applications.models import Application
from candidates.models import CandidateProfile

from .models import Job, Skill


def dashboard(request):
    applications = Application.objects.all()
    total_applications = applications.count()
    interview_count = applications.filter(status=Application.Status.INTERVIEW).count()
    accepted_count = applications.filter(status=Application.Status.ACCEPTED).count()
    context = {
        "total_candidates": CandidateProfile.objects.count(),
        "open_jobs": Job.objects.filter(status=Job.Status.OPEN).count(),
        "total_applications": total_applications,
        "interview_rate": round(interview_count / total_applications * 100, 1) if total_applications else 0,
        "accepted_rate": round(accepted_count / total_applications * 100, 1) if total_applications else 0,
        "average_matching": applications.filter(matching_score__isnull=False).aggregate(value=Avg("matching_score"))["value"] or 0,
        "top_skills": Skill.objects.annotate(demand=Count("job_skills")).order_by("-demand", "name")[:10],
        "salary_by_position": Job.objects.filter(salary_min__isnull=False, salary_max__isnull=False).values("title").annotate(
            average=Avg(ExpressionWrapper((F("salary_min") + F("salary_max")) / 2, output_field=FloatField()))
        ).order_by("-average")[:10],
    }
    return render(request, "jobs/dashboard.html", context)
