import io
import json
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from applications.models import Application
from candidates.models import CandidateProfile, CandidateSkill
from employers.models import EmployerProfile
from jobs.models import Job, JobSkill, Skill


def make_pdf(text):
    content = f"BT /F1 12 Tf 40 700 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(output))
        output += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(output)
    output += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        output += b"%010d 00000 n \n" % offset
    output += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(output)


class ApiAiBiTests(TestCase):
    def setUp(self):
        # Tạo skills
        self.skill_python = Skill.objects.create(name="Python", category="IT")
        self.skill_sql = Skill.objects.create(name="SQL", category="IT")
        self.skill_react = Skill.objects.create(name="React", category="IT")

        # Employer & Job
        self.employer_user = User.objects.create_user(
            username="emp_test", email="emp@test.com", password="Pass123!Test", role=User.Role.EMPLOYER
        )
        self.employer = EmployerProfile.objects.create(user=self.employer_user, company_name="Tech Corp")
        self.job = Job.objects.create(
            employer=self.employer,
            title="Python Developer",
            description="Tìm kiếm kỹ sư Python, SQL.",
            requirements="Python, SQL",
            location="Hà Nội",
            salary_min=15_000_000,
            salary_max=25_000_000,
            status=Job.Status.OPEN,
            deadline=timezone.localdate() + timedelta(days=30),
        )
        JobSkill.objects.create(job=self.job, skill=self.skill_python, importance=JobSkill.Importance.REQUIRED)
        JobSkill.objects.create(job=self.job, skill=self.skill_sql, importance=JobSkill.Importance.REQUIRED)

        # Candidate
        self.cand_user = User.objects.create_user(
            username="cand_test", email="cand@test.com", password="Pass123!Test", role=User.Role.CANDIDATE
        )
        self.candidate = CandidateProfile.objects.create(
            user=self.cand_user,
            major="Công nghệ thông tin",
            location="Hà Nội",
            experience_years=2,
            desired_salary=18_000_000,
        )
        CandidateSkill.objects.create(candidate=self.candidate, skill=self.skill_python)
        CandidateSkill.objects.create(candidate=self.candidate, skill=self.skill_sql)

        # Application
        self.application = Application.objects.create(
            candidate=self.candidate,
            job=self.job,
            matching_score=85.0,
            matching_explanation={"method": "rule_based", "matched_skills": ["Python", "SQL"]},
            status=Application.Status.APPLIED,
        )

    def test_bi_summary_api(self):
        url = reverse("api-bi-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("total_candidates", data["data"])
        self.assertIn("open_jobs", data["data"])
        self.assertIn("average_matching", data["data"])
        self.assertGreaterEqual(data["data"]["total_jobs"], 1)

    def test_bi_skills_api(self):
        url = reverse("api-bi-skills")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIsInstance(data["data"], list)
        skill_names = [s["name"] for s in data["data"]]
        self.assertTrue("Python" in skill_names or "SQL" in skill_names)

    def test_bi_salary_api(self):
        url = reverse("api-bi-salary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(len(data["data"]) >= 1)
        self.assertEqual(data["data"][0]["title"], "Python Developer")
        self.assertEqual(data["data"][0]["average"], 20_000_000)

    def test_bi_funnel_api(self):
        url = reverse("api-bi-funnel")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("stages", data)
        self.assertEqual(data["total"], 1)

    def test_bi_trend_api(self):
        url = reverse("api-bi-trend")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("labels", data)
        self.assertIn("jobs", data)
        self.assertIn("applications", data)

    def test_match_preview_api_authenticated_candidate(self):
        self.client.force_login(self.cand_user)
        url = reverse("api-match-preview")
        response = self.client.get(f"{url}?job_id={self.job.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["job_id"], self.job.id)
        self.assertGreaterEqual(data["score"], 0)
        self.assertIn("matched_skills", data["explanation"])

    def test_match_preview_unauthenticated(self):
        url = reverse("api-match-preview")
        response = self.client.get(f"{url}?job_id={self.job.id}")
        self.assertEqual(response.status_code, 401)

    def test_cv_parse_api_with_pdf(self):
        url = reverse("api-cv-parse")
        pdf_bytes = make_pdf("Python SQL Developer - 2 nam kinh nghiem dai hoc")
        uploaded = SimpleUploadedFile("cv.pdf", pdf_bytes, content_type="application/pdf")

        response = self.client.post(url, {"file": uploaded})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("Python", data["extracted"]["skills"])

    def test_cv_parse_api_with_text(self):
        url = reverse("api-cv-parse")
        response = self.client.post(url, {"text": "Tôi có 2 năm kinh nghiệm làm SQL và Python. Tốt nghiệp đại học."})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("SQL", data["extracted"]["skills"])
        self.assertEqual(data["extracted"]["experience_years"], 2.0)

    def test_rescore_job_api_by_employer(self):
        self.client.force_login(self.employer_user)
        url = reverse("api-match-rescore", args=[self.job.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["rescored_count"], 1)
        self.assertEqual(len(data["applications"]), 1)
        self.assertEqual(data["applications"][0]["id"], self.application.id)

    def test_update_application_status_api(self):
        self.client.force_login(self.employer_user)
        url = reverse("api-application-status", args=[self.application.id])
        response = self.client.post(
            url,
            data=json.dumps({"status": "INTERVIEW"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["new_status"], "INTERVIEW")

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "INTERVIEW")
