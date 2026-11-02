from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Application(models.Model):
    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Đã ứng tuyển"
        REVIEWING = "REVIEWING", "Đang xem xét"
        INTERVIEW = "INTERVIEW", "Phỏng vấn"
        ACCEPTED = "ACCEPTED", "Đã nhận"
        REJECTED = "REJECTED", "Từ chối"
        WITHDRAWN = "WITHDRAWN", "Đã rút hồ sơ"

    candidate = models.ForeignKey("candidates.CandidateProfile", on_delete=models.CASCADE, related_name="applications")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="applications")
    resume = models.ForeignKey("candidates.Resume", on_delete=models.SET_NULL, null=True, blank=True, related_name="applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    cover_letter = models.TextField(blank=True)
    matching_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    matching_explanation = models.JSONField(default=dict, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["candidate", "job"], name="unique_candidate_job_application")]
        ordering = ["-applied_at"]
        indexes = [models.Index(fields=["status", "applied_at"]), models.Index(fields=["matching_score"])]

    def clean(self):
        if self.job_id and self.job.status != self.job.Status.OPEN:
            raise ValidationError("Chỉ có thể ứng tuyển vào tin đang mở.")
        if self.job_id and self.job.deadline and self.job.deadline < timezone.localdate():
            raise ValidationError("Tin tuyển dụng đã hết hạn.")

    def __str__(self):
        return f"{self.candidate} - {self.job}"
