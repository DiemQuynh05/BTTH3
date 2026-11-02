from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [models.Index(fields=["category"])]


class Job(models.Model):
    class WorkMode(models.TextChoices):
        ONSITE = "ONSITE", "Tại văn phòng"
        HYBRID = "HYBRID", "Hybrid"
        REMOTE = "REMOTE", "Remote"

    class JobType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Toàn thời gian"
        PART_TIME = "PART_TIME", "Bán thời gian"
        INTERNSHIP = "INTERNSHIP", "Thực tập"
        REMOTE = "REMOTE", "Từ xa"

    class Experience(models.TextChoices):
        ENTRY = "ENTRY", "Mới tốt nghiệp"
        JUNIOR = "JUNIOR", "Junior"
        MID = "MID", "Middle"
        SENIOR = "SENIOR", "Senior"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Bản nháp"
        OPEN = "OPEN", "Đang tuyển"
        CLOSED = "CLOSED", "Đã đóng"

    employer = models.ForeignKey("employers.EmployerProfile", on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField()
    responsibilities = models.TextField(blank=True)
    location = models.CharField(max_length=255)
    work_mode = models.CharField(max_length=10, choices=WorkMode.choices, default=WorkMode.ONSITE)
    education_level = models.CharField(max_length=150, blank=True)
    openings = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    salary_min = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, validators=[MinValueValidator(0)])
    salary_max = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, validators=[MinValueValidator(0)])
    experience_level = models.CharField(max_length=20, choices=Experience.choices, default=Experience.ENTRY)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    deadline = models.DateField(null=True, blank=True)
    skills = models.ManyToManyField(Skill, through="JobSkill", related_name="jobs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        errors = {}
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            errors["salary_max"] = "Mức lương tối đa phải lớn hơn hoặc bằng mức tối thiểu."
        if self.deadline and self.deadline < timezone.localdate() and self.status == self.Status.OPEN:
            errors["deadline"] = "Hạn ứng tuyển phải từ hôm nay trở đi."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(salary_min__isnull=True) | Q(salary_max__isnull=True) | Q(salary_min__lte=F("salary_max")),
                name="job_salary_range_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["title"]),
            models.Index(fields=["location"]),
            models.Index(fields=["job_type"]),
        ]


class JobSkill(models.Model):
    class Importance(models.TextChoices):
        REQUIRED = "REQUIRED", "Bắt buộc"
        PREFERRED = "PREFERRED", "Ưu tiên"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="job_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="job_skills")
    importance = models.CharField(max_length=20, choices=Importance.choices, default=Importance.PREFERRED)
    minimum_years = models.DecimalField(max_digits=4, decimal_places=1, default=0, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["job", "skill"], name="unique_job_skill")]

    def __str__(self):
        return f"{self.job} - {self.skill}"
