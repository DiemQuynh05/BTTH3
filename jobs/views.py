from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from applications.forms import ApplicationForm
from applications.models import Application

from .forms import JobForm
from .models import Job, Skill


def home(request):
    featured = Job.objects.filter(status=Job.Status.OPEN).select_related("employer").order_by("-created_at")[:6]
    categories = Skill.objects.values("category").exclude(category="").distinct()[:8]
    return render(request, "jobs/home.html", {"featured_jobs": featured, "categories": categories})


def job_list(request):
    qs = Job.objects.filter(status=Job.Status.OPEN).select_related("employer").order_by("-created_at")
    keyword = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    job_type = request.GET.get("job_type", "").strip()
    if keyword:
        qs = qs.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword) | Q(employer__company_name__icontains=keyword))
    if location:
        qs = qs.filter(location__icontains=location)
    if job_type:
        qs = qs.filter(job_type=job_type)
    page = Paginator(qs, 9).get_page(request.GET.get("page"))
    return render(request, "jobs/list.html", {"page": page, "job_types": Job.JobType.choices, "filters": request.GET})


def job_detail(request, pk):
    job = get_object_or_404(Job.objects.select_related("employer").prefetch_related("skills"), pk=pk)
    applied = request.user.is_authenticated and Application.objects.filter(job=job, candidate__user=request.user).exists()
    return render(request, "jobs/detail.html", {"job": job, "applied": applied, "application_form": ApplicationForm()})


def _employer(request):
    return getattr(request.user, "employer_profile", None)


@login_required
def employer_job_list(request):
    employer = _employer(request)
    if employer is None:
        return render(request, "errors/403.html", status=403)
    jobs = employer.jobs.order_by("-updated_at")
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
def employer_job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk, employer__user=request.user)
    if request.method == "POST":
        job.delete()
        messages.success(request, "Tin tuyển dụng đã được xóa.")
        return redirect("employer-job-list")
    return render(request, "jobs/confirm_delete.html", {"job": job})
