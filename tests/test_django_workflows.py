from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError

from accounts.models import User
from applications.models import Application
from candidates.models import CandidateProfile
from employers.models import EmployerProfile
from jobs.models import Job


class RecruitmentWorkflowTests(TestCase):
    def setUp(self):
        self.candidate = User.objects.create_user(username="candidate", email="candidate@example.com", password="StrongPass123", role=User.Role.CANDIDATE)
        CandidateProfile.objects.create(user=self.candidate)
        self.employer = User.objects.create_user(username="employer", email="employer@example.com", password="StrongPass123", role=User.Role.EMPLOYER)
        company = EmployerProfile.objects.create(user=self.employer, company_name="Test Co")
        self.job = Job.objects.create(employer=company, title="Django Developer", description="Build apps", requirements="Django", location="HCM", status=Job.Status.OPEN, deadline=timezone.localdate() + timedelta(days=5))

    def test_registration_creates_candidate_profile(self):
        response = self.client.post(reverse("register"), {"username": "new", "email": "new@example.com", "role": "CANDIDATE", "password1": "StrongPass123!", "password2": "StrongPass123!"})
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(CandidateProfile.objects.filter(user__username="new").exists())

    def test_employer_cannot_edit_other_employer_job(self):
        self.client.login(username="employer", password="StrongPass123")
        other = User.objects.create_user(username="other", email="other@example.com", password="StrongPass123", role=User.Role.EMPLOYER)
        EmployerProfile.objects.create(user=other, company_name="Other Co")
        self.client.force_login(other)
        response = self.client.get(reverse("employer-job-edit", args=[self.job.pk]))
        self.assertEqual(response.status_code, 404)

    def test_candidate_cannot_apply_twice(self):
        self.client.force_login(self.candidate)
        data = {"cover_letter": "Interested"}
        response = self.client.post(reverse("application-apply", args=[self.job.pk]), data)
        self.assertRedirects(response, reverse("application-list"))
        self.client.post(reverse("application-apply", args=[self.job.pk]), data)
        self.assertEqual(Application.objects.filter(candidate__user=self.candidate, job=self.job).count(), 1)

    def test_job_rejects_invalid_salary_range(self):
        self.job.salary_min = 20_000_000
        self.job.salary_max = 10_000_000
        with self.assertRaises(ValidationError):
            self.job.full_clean()
