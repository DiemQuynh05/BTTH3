from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models


class CandidateProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="candidate_profile")
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    education = models.TextField(blank=True)
    major = models.CharField(max_length=150, blank=True)
    year_of_study = models.PositiveSmallIntegerField(null=True, blank=True)
    experience_years = models.DecimalField(max_digits=4, decimal_places=1, default=0, validators=[MinValueValidator(0)])
    desired_salary = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, validators=[MinValueValidator(0)])
    projects = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["location"]), models.Index(fields=["major"])]

    def __str__(self):
        return f"Hồ sơ {self.user}"


class Resume(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="resumes")
    file = models.FileField(upload_to="resumes/", validators=[FileExtensionValidator(["pdf", "doc", "docx"])])
    original_filename = models.CharField(max_length=255)
    resume_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_filename


class CandidateSkill(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="candidate_skills")
    skill = models.ForeignKey("jobs.Skill", on_delete=models.CASCADE, related_name="candidate_skills")
    proficiency_level = models.CharField(max_length=30, default="Trung bình")
    experience_years = models.DecimalField(max_digits=4, decimal_places=1, default=0, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["candidate", "skill"], name="unique_candidate_skill")]

    def __str__(self):
        return f"{self.candidate} - {self.skill}"
