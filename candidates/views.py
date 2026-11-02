from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from jobs.models import Skill

from .forms import CandidateProfileForm, ResumeForm
from .models import CandidateProfile, CandidateSkill
from .services import process_resume


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
            process_resume(resume)
            if resume.parsed_data.get("extracted_from_file"):
                messages.success(request, f"CV đã được tải lên và phân tích: nhận diện {len(resume.parsed_data['skills'])} kỹ năng.")
            else:
                messages.warning(request, "CV đã được tải lên nhưng không đọc được nội dung. Hệ thống hỗ trợ phân tích PDF dạng văn bản và DOCX.")
            return redirect("candidate-profile")

        if "skill_add_submit" in request.POST:
            skill_name = request.POST.get("skill_name", "").strip()
            level = int(request.POST.get("proficiency_level", 3) or 3)
            years = float(request.POST.get("years_of_experience", 1.0) or 1.0)
            if skill_name:
                skill_obj, _ = Skill.objects.get_or_create(name=skill_name)
                cand_skill, created = CandidateSkill.objects.get_or_create(
                    candidate=candidate, skill=skill_obj,
                    defaults={"proficiency_level": level, "years_of_experience": years}
                )
                if not created:
                    cand_skill.proficiency_level = level
                    cand_skill.years_of_experience = years
                    cand_skill.save()
                messages.success(request, f"Đã cập nhật kỹ năng '{skill_name}'.")
            return redirect("candidate-profile")

        if "skill_delete_id" in request.POST:
            CandidateSkill.objects.filter(candidate=candidate, pk=request.POST.get("skill_delete_id")).delete()
            messages.success(request, "Đã xóa kỹ năng khỏi hồ sơ.")
            return redirect("candidate-profile")

    candidate_skills = candidate.candidate_skills.select_related("skill").order_by("skill__name")
    applications = candidate.applications.select_related("job", "job__employer").order_by("-applied_at")[:10]
    all_skills = Skill.objects.all().order_by("name")

    return render(request, "candidates/profile.html", {
        "form": form,
        "resume_form": resume_form,
        "candidate": candidate,
        "candidate_skills": candidate_skills,
        "applications": applications,
        "all_skills": all_skills,
    })


@login_required
def delete_resume(request, pk):
    resume = get_object_or_404(request.user.candidate_profile.resumes, pk=pk)
    if request.method == "POST":
        resume.delete()
        messages.success(request, "CV đã được xóa.")
    return redirect("candidate-profile")
