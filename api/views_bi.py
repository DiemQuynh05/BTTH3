from datetime import timedelta
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Max, Min
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from applications.matching import matching_method_label
from applications.models import Application
from candidates.models import CandidateProfile, CandidateSkill
from jobs.models import Job, JobSkill, Skill


@require_http_methods(["GET"])
def bi_summary(request):
    """Tổng quan KPI hệ thống tuyển dụng."""
    applications = Application.objects.all()
    total_applications = applications.count()
    interview_count = applications.filter(status=Application.Status.INTERVIEW).count()
    accepted_count = applications.filter(status=Application.Status.ACCEPTED).count()
    avg_matching = applications.filter(matching_score__isnull=False).aggregate(value=Avg("matching_score"))["value"] or 0

    return JsonResponse({
        "status": "success",
        "data": {
            "total_candidates": CandidateProfile.objects.count(),
            "total_jobs": Job.objects.count(),
            "open_jobs": Job.objects.filter(status=Job.Status.OPEN).count(),
            "total_applications": total_applications,
            "interview_rate": round(interview_count / total_applications * 100, 1) if total_applications else 0,
            "accepted_rate": round(accepted_count / total_applications * 100, 1) if total_applications else 0,
            "average_matching": round(avg_matching, 1),
            "matching_method": matching_method_label(),
        }
    })


@require_http_methods(["GET"])
def bi_skills(request):
    """Top kỹ năng theo nhu cầu thị trường (Demand) và nguồn cung ứng viên (Supply)."""
    limit = int(request.GET.get("limit", 10))

    # Demand: số lần xuất hiện trong JobSkill
    top_demand = list(
        JobSkill.objects.values("skill__name")
        .annotate(demand=Count("id"))
        .order_by("-demand")[:limit]
    )

    skill_names = [item["skill__name"] for item in top_demand]

    # Supply tương ứng: số ứng viên sở hữu kỹ năng đó
    supply_map = dict(
        CandidateSkill.objects.filter(skill__name__in=skill_names)
        .values("skill__name")
        .annotate(supply=Count("id"))
        .values_list("skill__name", "supply")
    )

    skills_data = []
    for item in top_demand:
        name = item["skill__name"]
        demand = item["demand"]
        supply = supply_map.get(name, 0)
        skills_data.append({
            "name": name,
            "demand": demand,
            "supply": supply,
            "gap": demand - supply,  # >0: Thiếu hụt nguồn nhân lực
        })

    return JsonResponse({
        "status": "success",
        "count": len(skills_data),
        "data": skills_data,
    })


@require_http_methods(["GET"])
def bi_salary(request):
    """Thống kê phân bố lương trung bình, tối thiểu, tối đa theo chức danh vị trí."""
    limit = int(request.GET.get("limit", 10))

    salary_data = list(
        Job.objects.filter(salary_min__isnull=False, salary_max__isnull=False)
        .values("title")
        .annotate(
            count=Count("id"),
            min_salary=Min("salary_min"),
            max_salary=Max("salary_max"),
            avg_salary=Avg(
                ExpressionWrapper(
                    (F("salary_min") + F("salary_max")) / 2,
                    output_field=FloatField()
                )
            ),
        )
        .order_by("-avg_salary")[:limit]
    )

    formatted = [
        {
            "title": item["title"],
            "count": item["count"],
            "min": float(item["min_salary"]) if item["min_salary"] is not None else 0,
            "max": float(item["max_salary"]) if item["max_salary"] is not None else 0,
            "average": round(item["avg_salary"], 0) if item["avg_salary"] is not None else 0,
        }
        for item in salary_data
    ]

    return JsonResponse({
        "status": "success",
        "data": formatted,
    })


@require_http_methods(["GET"])
def bi_funnel(request):
    """Thống kê phễu tuyển dụng qua các giai đoạn."""
    total = Application.objects.count()
    status_counts = dict(
        Application.objects.values("status").annotate(count=Count("id")).values_list("status", "count")
    )

    submitted = total
    reviewing = status_counts.get("REVIEWING", 0) + status_counts.get("APPLIED", 0)
    interview = status_counts.get("INTERVIEW", 0)
    accepted = status_counts.get("ACCEPTED", 0)
    rejected = status_counts.get("REJECTED", 0)

    stages = [
        {"stage": "Hồ sơ ứng tuyển", "count": submitted, "rate": 100.0},
        {
            "stage": "Đang xem xét / Đạt sơ tuyển",
            "count": reviewing + interview + accepted,
            "rate": round((reviewing + interview + accepted) / total * 100, 1) if total else 0,
        },
        {
            "stage": "Mời phỏng vấn",
            "count": interview + accepted,
            "rate": round((interview + accepted) / total * 100, 1) if total else 0,
        },
        {
            "stage": "Trúng tuyển (Offer)",
            "count": accepted,
            "rate": round(accepted / total * 100, 1) if total else 0,
        },
    ]

    return JsonResponse({
        "status": "success",
        "total": total,
        "rejected": rejected,
        "stages": stages,
    })


@require_http_methods(["GET"])
def bi_trend(request):
    """Xu hướng đăng tin và nộp hồ sơ theo thời gian gần đây (30 ngày)."""
    days = int(request.GET.get("days", 30))
    since = timezone.now() - timedelta(days=days)

    jobs_by_date = dict(
        Job.objects.filter(created_at__gte=since)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .values_list("date", "count")
    )

    apps_by_date = dict(
        Application.objects.filter(applied_at__gte=since)
        .annotate(date=TruncDate("applied_at"))
        .values("date")
        .annotate(count=Count("id"))
        .values_list("date", "count")
    )

    # Tổng hợp danh sách ngày liên tục
    all_dates = []
    current = since.date()
    today = timezone.localdate()
    while current <= today:
        all_dates.append(current)
        current += timedelta(days=1)

    labels = [d.strftime("%d/%m") for d in all_dates]
    job_counts = [jobs_by_date.get(d, 0) for d in all_dates]
    app_counts = [apps_by_date.get(d, 0) for d in all_dates]

    return JsonResponse({
        "status": "success",
        "labels": labels,
        "jobs": job_counts,
        "applications": app_counts,
    })
