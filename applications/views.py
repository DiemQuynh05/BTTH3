from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from candidates.models import CandidateProfile
from jobs.models import Job

from .forms import ApplicationForm
from .models import Application


@login_required
def apply(request, job_id):
    if request.user.role != request.user.Role.CANDIDATE:
        return render(request, "errors/403.html", status=403)
    job = get_object_or_404(Job, pk=job_id)
    candidate, _ = CandidateProfile.objects.get_or_create(user=request.user)
    if Application.objects.filter(candidate=candidate, job=job).exists():
        messages.error(request, "Bạn đã ứng tuyển tin này.")
        return redirect("job-detail", pk=job.pk)
    form = ApplicationForm(request.POST or None)
    form.fields["resume"].queryset = candidate.resumes.all()
    if request.method == "POST" and form.is_valid():
        application = form.save(commit=False)
        application.candidate = candidate
        application.job = job
        try:
            application.full_clean()
            application.save()
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Ứng tuyển thành công.")
            return redirect("application-list")
    return render(request, "applications/apply.html", {"form": form, "job": job})


@login_required
def application_list(request):
    if request.user.role != request.user.Role.CANDIDATE:
        return render(request, "errors/403.html", status=403)
    applications = Application.objects.filter(candidate__user=request.user).select_related("job", "job__employer")
    return render(request, "applications/list.html", {"applications": applications})
