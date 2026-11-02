from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render

from applications.forms import ApplicationForm
from applications.matching import calculate_matching_score, rescore_applications
from applications.models import Application
from candidates.models import CandidateProfile

from .forms import JobForm
from .models import Job, Skill


def home(request):
    featured = Job.objects.filter(status=Job.Status.OPEN).select_related("employer").prefetch_related("skills", "job_skills__skill").order_by("-created_at")[:6]
    categories = Skill.objects.values("category").exclude(category="").distinct()[:8]
    all_skills = list(Skill.objects.values_list("name", flat=True).order_by("name"))
    stats = {
        "jobs_count": Job.objects.filter(status=Job.Status.OPEN).count(),
        "candidates_count": CandidateProfile.objects.count(),
        "applications_count": Application.objects.count(),
    }
    return render(request, "jobs/home.html", {
        "featured_jobs": featured,
        "categories": categories,
        "all_skills": all_skills,
        "stats": stats,
    })


def job_list(request):
    qs = Job.objects.filter(status=Job.Status.OPEN).select_related("employer").prefetch_related("skills", "job_skills__skill").order_by("-created_at")
    keyword = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    job_type = request.GET.get("job_type", "").strip()
    skill_filter = request.GET.get("skill", "").strip()

    if keyword:
        qs = qs.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword) | Q(employer__company_name__icontains=keyword))
    if location:
        qs = qs.filter(location__icontains=location)
    if job_type:
        qs = qs.filter(job_type=job_type)
    if skill_filter:
        qs = qs.filter(skills__name__iexact=skill_filter)

    page = Paginator(qs, 9).get_page(request.GET.get("page"))

    # Danh sách kỹ năng phổ biến để lọc
    popular_skills = Skill.objects.annotate(job_count=Count("job_skills")).filter(job_count__gt=0).order_by("-job_count")[:15]
    all_skills = list(Skill.objects.values_list("name", flat=True).order_by("name"))

    return render(request, "jobs/list.html", {
        "page": page,
        "job_types": Job.JobType.choices,
        "filters": request.GET,
        "popular_skills": popular_skills,
        "all_skills": all_skills,
    })


def job_detail(request, pk):
    job = get_object_or_404(Job.objects.select_related("employer").prefetch_related("skills", "job_skills__skill"), pk=pk)
    applied = False
    match = None

    if request.user.is_authenticated:
        applied = Application.objects.filter(job=job, candidate__user=request.user).exists()
        # Tạo profile tự động cho ứng viên hoặc superuser nếu chưa có
        if request.user.role == request.user.Role.CANDIDATE or request.user.is_superuser:
            candidate, _ = CandidateProfile.objects.get_or_create(user=request.user)
            score, explanation = calculate_matching_score(candidate, job)
            from api.views_ai import _enrich_explanation
            match = {"score": score, "explanation": _enrich_explanation(explanation, candidate, job)}

    return render(request, "jobs/detail.html", {
        "job": job,
        "applied": applied,
        "application_form": ApplicationForm(),
        "match": match,
    })


def _employer(request):
    return getattr(request.user, "employer_profile", None)


@login_required
def employer_job_list(request):
    employer = _employer(request)
    if employer is None:
        return render(request, "errors/403.html", status=403)
    jobs = employer.jobs.annotate(applicant_count=Count("applications")).prefetch_related("skills").order_by("-updated_at")
    return render(request, "jobs/employer_list.html", {"jobs": jobs})


@login_required
def employer_job_create(request):
    employer = _employer(request)
    if employer is None:
        return render(request, "errors/403.html", status=403)
    form = JobForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        job = form.save(commit=False)
        job.employer = employer
        job.save()
        messages.success(request, "Tin tuyển dụng đã được tạo.")
        return redirect("employer-job-list")
    return render(request, "jobs/form.html", {"form": form, "title": "Tạo tin tuyển dụng"})


@login_required
def employer_job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk, employer__user=request.user)
    form = JobForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tin tuyển dụng đã được cập nhật.")
        return redirect("employer-job-list")
    return render(request, "jobs/form.html", {"form": form, "title": "Chỉnh sửa tin tuyển dụng"})


@login_required
def employer_job_applicants(request, pk):
    job = get_object_or_404(Job, pk=pk, employer__user=request.user)
    if request.method == "POST":
        count = rescore_applications(job.applications.all())
        messages.success(request, f"Đã tính lại điểm tương thích cho {count} hồ sơ.")
        return redirect("employer-job-applicants", pk=job.pk)
    applications = list(job.applications.select_related("candidate__user", "resume").order_by(
        F("matching_score").desc(nulls_last=True), "-applied_at"
    ))
    high_score_count = sum(1 for a in applications if a.matching_score and a.matching_score >= 70)
    interview_count = sum(1 for a in applications if a.status == Application.Status.INTERVIEW)
    accepted_count = sum(1 for a in applications if a.status == Application.Status.ACCEPTED)

    return render(request, "jobs/applicants.html", {
        "job": job,
        "applications": applications,
        "high_score_count": high_score_count,
        "interview_count": interview_count,
        "accepted_count": accepted_count,
    })


@login_required
def employer_job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk, employer__user=request.user)
    if request.method == "POST":
        job.delete()
        messages.success(request, "Tin tuyển dụng đã được xóa.")
        return redirect("employer-job-list")
    return render(request, "jobs/confirm_delete.html", {"job": job})
