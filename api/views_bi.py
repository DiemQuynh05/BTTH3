from datetime import timedelta
from django.core.cache import cache
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Max, Min, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from applications.matching import matching_method_label
from applications.models import Application
from candidates.models import CandidateProfile, CandidateSkill
from jobs.models import Job, JobSkill, Skill


CACHE_TTL = 300  # 5 phút


def _get_filter_qs(request):
    """Lấy filter parameters chung cho các endpoint BI."""
    days = request.GET.get("days")
    job_type = request.GET.get("job_type", "").strip()
    industry = request.GET.get("industry", "").strip()

    job_q = Q()
    app_q = Q()

    if days:
        try:
            d = int(days)
            if d > 0:
                since = timezone.now() - timedelta(days=d)
                job_q &= Q(created_at__gte=since)
                app_q &= Q(applied_at__gte=since)
        except (ValueError, TypeError):
            pass

    if job_type:
        job_q &= Q(job_type=job_type)
        app_q &= Q(job__job_type=job_type)

    if industry:
        job_q &= Q(employer__industry__icontains=industry)
        app_q &= Q(job__employer__industry__icontains=industry)

    return job_q, app_q


@require_http_methods(["GET"])
def bi_summary(request):
    """Tổng quan KPI hệ thống tuyển dụng có hỗ trợ bộ lọc và cache."""
    cache_key = f"bi_summary_{request.GET.urlencode()}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return JsonResponse(cached_data)

    job_q, app_q = _get_filter_qs(request)
    applications = Application.objects.filter(app_q)
    total_applications = applications.count()
    interview_count = applications.filter(status=Application.Status.INTERVIEW).count()
    accepted_count = applications.filter(status=Application.Status.ACCEPTED).count()
    avg_matching = applications.filter(matching_score__isnull=False).aggregate(value=Avg("matching_score"))["value"] or 0

    jobs = Job.objects.filter(job_q)
    total_jobs = jobs.count()
    open_jobs = jobs.filter(status=Job.Status.OPEN).count()

    response_data = {
        "status": "success",
        "data": {
            "total_candidates": CandidateProfile.objects.count(),
            "total_jobs": total_jobs,
            "open_jobs": open_jobs,
            "total_applications": total_applications,
            "interview_rate": round(interview_count / total_applications * 100, 1) if total_applications else 0,
            "accepted_rate": round(accepted_count / total_applications * 100, 1) if total_applications else 0,
            "average_matching": round(avg_matching, 1),
            "matching_method": matching_method_label(),
        }
    }
    cache.set(cache_key, response_data, CACHE_TTL)
    return JsonResponse(response_data)


@require_http_methods(["GET"])
def bi_skills(request):
    """Top kỹ năng theo nhu cầu thị trường (Demand) và nguồn cung ứng viên (Supply)."""
    cache_key = f"bi_skills_{request.GET.urlencode()}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return JsonResponse(cached_data)

    limit = int(request.GET.get("limit", 10))
    job_q, _ = _get_filter_qs(request)

    # Lọc JobSkill theo filter jobs
    job_skills_qs = JobSkill.objects.filter(job__in=Job.objects.filter(job_q)) if job_q else JobSkill.objects.all()

    top_demand = list(
        job_skills_qs.values("skill__name")
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

    response_data = {
        "status": "success",
        "count": len(skills_data),
        "data": skills_data,
    }
    cache.set(cache_key, response_data, CACHE_TTL)
    return JsonResponse(response_data)


@require_http_methods(["GET"])
def bi_salary(request):
    """Thống kê phân bố lương trung bình, tối thiểu, tối đa theo chức danh vị trí."""
    cache_key = f"bi_salary_{request.GET.urlencode()}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return JsonResponse(cached_data)

    limit = int(request.GET.get("limit", 10))
    job_q, _ = _get_filter_qs(request)
    base_qs = Job.objects.filter(salary_min__isnull=False, salary_max__isnull=False)
    if job_q:
        base_qs = base_qs.filter(job_q)

    salary_data = list(
        base_qs.values("title")
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

    response_data = {
        "status": "success",
        "data": formatted,
    }
    cache.set(cache_key, response_data, CACHE_TTL)
    return JsonResponse(response_data)


@require_http_methods(["GET"])
def bi_funnel(request):
    """Thống kê phễu tuyển dụng qua các giai đoạn."""
    cache_key = f"bi_funnel_{request.GET.urlencode()}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return JsonResponse(cached_data)

    _, app_q = _get_filter_qs(request)
    apps_qs = Application.objects.filter(app_q) if app_q else Application.objects.all()

    total = apps_qs.count()
    status_counts = dict(
        apps_qs.values("status").annotate(count=Count("id")).values_list("status", "count")
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

    response_data = {
        "status": "success",
        "total": total,
        "rejected": rejected,
        "stages": stages,
    }
    cache.set(cache_key, response_data, CACHE_TTL)
    return JsonResponse(response_data)


@require_http_methods(["GET"])
def bi_trend(request):
    """Xu hướng đăng tin và nộp hồ sơ theo thời gian gần đây."""
    cache_key = f"bi_trend_{request.GET.urlencode()}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return JsonResponse(cached_data)

    days = int(request.GET.get("days", 30))
    job_type = request.GET.get("job_type", "").strip()
    since = timezone.now() - timedelta(days=days)

    jobs_base = Job.objects.filter(created_at__gte=since)
    apps_base = Application.objects.filter(applied_at__gte=since)

    if job_type:
        jobs_base = jobs_base.filter(job_type=job_type)
        apps_base = apps_base.filter(job__job_type=job_type)

    jobs_by_date = dict(
        jobs_base.annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .values_list("date", "count")
    )

    apps_by_date = dict(
        apps_base.annotate(date=TruncDate("applied_at"))
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

    response_data = {
        "status": "success",
        "labels": labels,
        "jobs": job_counts,
        "applications": app_counts,
    }
    cache.set(cache_key, response_data, CACHE_TTL)
    return JsonResponse(response_data)


import json

@require_http_methods(["GET"])
def bi_all_export(request):
    """Xuất tổng hợp toàn bộ dữ liệu BI dạng JSON cho external tools (Metabase, Grafana) (C3.2)."""
    cache_key = f"bi_export_{request.GET.urlencode()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached)

    summary_res = json.loads(bi_summary(request).content)
    skills_res = json.loads(bi_skills(request).content)
    salary_res = json.loads(bi_salary(request).content)
    funnel_res = json.loads(bi_funnel(request).content)

    export_data = {
        "status": "success",
        "timestamp": timezone.now().isoformat(),
        "summary": summary_res.get("data", {}),
        "skills": skills_res.get("data", []),
        "salary": salary_res.get("data", []),
        "funnel": funnel_res.get("stages", []),
    }
    cache.set(cache_key, export_data, CACHE_TTL)
    return JsonResponse(export_data)
