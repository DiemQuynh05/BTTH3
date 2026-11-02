from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CANDIDATE = "CANDIDATE", "Ứng viên"
        EMPLOYER = "EMPLOYER", "Nhà tuyển dụng"
        ADMIN = "ADMIN", "Quản trị viên"

    email = models.EmailField("email", unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CANDIDATE)

    def __str__(self):
        return self.get_full_name() or self.username
