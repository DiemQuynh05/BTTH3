from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from candidates.models import CandidateProfile
from jobs.models import Job

from .forms import ApplicationForm
from .matching import calculate_matching_score
from .models import Application


@login_required
def apply(request, job_id):
    job = get_object_or_404(Job, pk=job_id)

    # Nếu là Employer không phải superuser thì nhắc nhở
    if request.user.role == request.user.Role.EMPLOYER and not request.user.is_superuser:
        messages.warning(request, "Bạn đang đăng nhập bằng tài khoản Nhà tuyển dụng. Vui lòng đăng nhập bằng tài khoản Ứng viên để nộp đơn ứng tuyển.")
        return redirect("job-detail", pk=job.pk)

    candidate, _ = CandidateProfile.objects.get_or_create(user=request.user)

    if Application.objects.filter(candidate=candidate, job=job).exists():
        messages.info(request, "Bạn đã ứng tuyển tin này trước đó.")
        return redirect("job-detail", pk=job.pk)

    form = ApplicationForm(request.POST or None)
    form.fields["resume"].queryset = candidate.resumes.all()
    if request.method == "POST" and form.is_valid():
        application = form.save(commit=False)
        application.candidate = candidate
        application.job = job
        try:
            application.full_clean()
            application.matching_score, application.matching_explanation = calculate_matching_score(candidate, job, application.resume)
            application.save()
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Ứng tuyển thành công! Bạn có thể theo dõi tiến trình trong mục Hồ sơ đã ứng tuyển.")
            return redirect("application-list")
    return render(request, "applications/apply.html", {"form": form, "job": job})


@login_required
def application_list(request):
    if request.user.role == request.user.Role.EMPLOYER and not request.user.is_superuser:
        messages.info(request, "Mục này dành cho Ứng viên theo dõi hồ sơ. Bạn đang ở tài khoản Nhà tuyển dụng.")
        return redirect("employer-job-list")

    candidate, _ = CandidateProfile.objects.get_or_create(user=request.user)
    applications = Application.objects.filter(candidate=candidate).select_related("job", "job__employer", "resume")
    return render(request, "applications/list.html", {"applications": applications})
