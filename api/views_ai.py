import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from applications.ai.cv_parser import (
    EDUCATION_LABELS,
    extract_text,
    parse_education_level,
    parse_experience_years,
)
from applications.matching import (
    calculate_matching_score,
    rescore_applications,
    skill_extractor,
)
from applications.models import Application
from candidates.models import CandidateProfile
from jobs.models import Job

logger = logging.getLogger(__name__)


def _enrich_explanation(explanation, candidate, job):
    """Bổ sung matched_skills và missing_required_skills nếu explanation chưa có (ví dụ rule-based)."""
    exp = dict(explanation or {})
    if "matched_skills" not in exp:
        cand_skills = set(candidate.candidate_skills.values_list("skill__name", flat=True))
        req_skills = set(job.job_skills.filter(importance="REQUIRED").values_list("skill__name", flat=True))
        pref_skills = set(job.job_skills.filter(importance="PREFERRED").values_list("skill__name", flat=True))
        exp["matched_skills"] = sorted(list((req_skills | pref_skills) & cand_skills))
        exp["missing_required_skills"] = sorted(list(req_skills - cand_skills))
    return exp


@require_http_methods(["GET", "POST"])
def match_preview(request):
    """Tính toán Matching Score cho ứng viên hiện tại hoặc theo tham số."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Vui lòng đăng nhập để xem độ tương thích."}, status=401)

    if request.method == "POST":
        try:
            data = json.loads(request.body) if request.body else {}
        except Exception:
            data = request.POST
        job_id = data.get("job_id") or request.GET.get("job_id")
    else:
        job_id = request.GET.get("job_id")

    if not job_id:
        return JsonResponse({"error": "Thiếu thông số job_id."}, status=400)

    job = get_object_or_404(Job.objects.select_related("employer").prefetch_related("skills", "job_skills__skill"), pk=job_id)
    candidate = getattr(request.user, "candidate_profile", None)

    if candidate is None:
        candidate_id = request.GET.get("candidate_id") or (data.get("candidate_id") if request.method == "POST" else None)
        if candidate_id:
            candidate = get_object_or_404(CandidateProfile, pk=candidate_id)
        else:
            return JsonResponse({"error": "Chỉ ứng viên mới có thể xem điểm tương thích cá nhân."}, status=400)

    score, explanation = calculate_matching_score(candidate, job)
    enriched_exp = _enrich_explanation(explanation, candidate, job)

    return JsonResponse({
        "status": "success",
        "job_id": job.id,
        "job_title": job.title,
        "score": float(score) if score is not None else 0.0,
        "explanation": enriched_exp,
    })


@require_http_methods(["POST"])
def cv_parse(request):
    """Trích xuất kỹ năng, kinh nghiệm và học vấn từ file CV (PDF/DOCX) hoặc text."""
    uploaded_file = request.FILES.get("file")
    raw_text = request.POST.get("text", "")

    if not uploaded_file and not raw_text:
        return JsonResponse({"error": "Vui lòng tải lên file CV (PDF/DOCX) hoặc cung cấp văn bản."}, status=400)

    filename = uploaded_file.name if uploaded_file else "cv.txt"
    if uploaded_file:
        file_bytes = uploaded_file.read()
        extracted_text = extract_text(file_bytes, filename)
    else:
        extracted_text = raw_text

    extractor = skill_extractor()
    found_skills_keys = extractor.extract(extracted_text)
    found_skill_names = extractor.names(found_skills_keys)

    exp_years = parse_experience_years(extracted_text)
    edu_level = parse_education_level(extracted_text)
    edu_label = EDUCATION_LABELS.get(edu_level, "Không xác định")

    return JsonResponse({
        "status": "success",
        "filename": filename,
        "extracted": {
            "skills": found_skill_names,
            "experience_years": exp_years if exp_years is not None else 0,
            "education_level": edu_level,
            "education_label": edu_label,
            "text_length": len(extracted_text),
            "preview_text": extracted_text[:400] + ("..." if len(extracted_text) > 400 else ""),
        }
    })


@require_http_methods(["POST"])
def rescore_job(request, job_id):
    """Tính lại Matching Score cho toàn bộ ứng viên của một tin tuyển dụng."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Chưa đăng nhập."}, status=401)

    job = get_object_or_404(Job, pk=job_id)
    if job.employer.user != request.user and not request.user.is_staff:
        return JsonResponse({"error": "Bạn không có quyền thực hiện thao tác này."}, status=403)

    count = rescore_applications(job.applications.all())

    # Lấy danh sách đã cập nhật
    applications = job.applications.select_related("candidate__user", "resume").order_by(
        "-matching_score", "-applied_at"
    )

    data = []
    for app in applications:
        exp = _enrich_explanation(app.matching_explanation, app.candidate, job)
        score_val = float(app.matching_score) if app.matching_score is not None else None
        data.append({
            "id": app.id,
            "candidate_name": app.candidate.user.get_full_name() or app.candidate.user.username,
            "location": app.candidate.location or "",
            "matching_score": score_val,
            "method": exp.get("method", "rule_based"),
            "matched_skills": exp.get("matched_skills", []),
            "missing_required_skills": exp.get("missing_required_skills", []),
            "required_skills_ratio": exp.get("required_skills", ""),
            "top_factors": exp.get("top_factors", [])[:3],
            "status": app.status,
            "status_display": app.get_status_display(),
            "resume_url": app.resume.file.url if app.resume and app.resume.file else None,
        })

    return JsonResponse({
        "status": "success",
        "message": f"Đã tính lại điểm tương thích cho {count} hồ sơ.",
        "rescored_count": count,
        "applications": data,
    })


@require_http_methods(["POST"])
def update_application_status(request, app_id):
    """Cập nhật trạng thái hồ sơ ứng tuyển từ phía Employer."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Chưa đăng nhập."}, status=401)

    app = get_object_or_404(Application.objects.select_related("job__employer"), pk=app_id)
    if app.job.employer.user != request.user and not request.user.is_staff:
        return JsonResponse({"error": "Không có quyền thực hiện."}, status=403)

    try:
        payload = json.loads(request.body) if request.body else request.POST
        new_status = payload.get("status")
    except Exception:
        new_status = request.POST.get("status")

    valid_statuses = [choice[0] for choice in Application.Status.choices]
    if new_status not in valid_statuses:
        return JsonResponse({"error": f"Trạng thái không hợp lệ. Cho phép: {valid_statuses}"}, status=400)

    app.status = new_status
    app.save(update_fields=["status"])

    return JsonResponse({
        "status": "success",
        "application_id": app.id,
        "new_status": app.status,
        "new_status_display": app.get_status_display(),
    })
