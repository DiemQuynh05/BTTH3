from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from jobs.models import Skill

from .forms import CandidateProfileForm, ResumeForm
from .models import CandidateProfile, CandidateSkill


@login_required
def profile(request):
    if request.user.role != request.user.Role.CANDIDATE:
        return render(request, "errors/403.html", status=403)
    candidate, _ = CandidateProfile.objects.get_or_create(user=request.user)
    form = CandidateProfileForm(request.POST or None, request.FILES or None, instance=candidate)
    resume_form = ResumeForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if "profile_submit" in request.POST and form.is_valid():
            form.save()
            messages.success(request, "Hồ sơ đã được cập nhật.")
            return redirect("candidate-profile")
        if "resume_submit" in request.POST and resume_form.is_valid():
            resume = resume_form.save(commit=False)
            resume.candidate = candidate
            resume.original_filename = resume.file.name
            resume.save()
            messages.success(request, "CV đã được tải lên.")
            return redirect("candidate-profile")
    return render(request, "candidates/profile.html", {"form": form, "resume_form": resume_form, "candidate": candidate})


@login_required
def delete_resume(request, pk):
    resume = get_object_or_404(request.user.candidate_profile.resumes, pk=pk)
    if request.method == "POST":
        resume.delete()
        messages.success(request, "CV đã được xóa.")
    return redirect("candidate-profile")
