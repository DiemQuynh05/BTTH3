import io
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from docx import Document

from accounts.models import User
from applications.ai.cv_parser import extract_text, parse_education_level, parse_experience_years
from applications.ai.features import CandidateDoc, JobDoc
from applications.ai.model import MatchingModel, train_matching_model
from applications.ai.skills import get_extractor
from applications.ai.synthetic import generate_training_data
from applications.ai.text import normalize_text
from applications.matching import calculate_matching_score
from applications.models import Application
from candidates.models import CandidateProfile, CandidateSkill, Resume
from employers.models import EmployerProfile
from jobs.models import Job, JobSkill, Skill

TEMP_DIR = None
MODEL_PATH = None


def setUpModule():
    global TEMP_DIR, MODEL_PATH
    TEMP_DIR = Path(tempfile.mkdtemp())
    MODEL_PATH = TEMP_DIR / "matching_model.joblib"
    candidates, jobs, labels = generate_training_data(800, seed=7)
    train_matching_model(candidates, jobs, labels, seed=7).save(MODEL_PATH)


def tearDownModule():
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


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


def make_docx(*paragraphs):
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class CvParsingTests(SimpleTestCase):
    def test_normalize_removes_vietnamese_diacritics(self):
        self.assertEqual(normalize_text("Kỹ năng: Phân tích DỮ LIỆU, Đà Nẵng"), "ky nang phan tich du lieu da nang")

    def test_extract_skills_handles_aliases_implications_and_word_boundaries(self):
        skills = get_extractor().extract("Thành thạo ReactJS, PowerBI, MS Excel; IELTS 7.0; viết HTML5 và Javascript")
        self.assertTrue({"react", "javascript", "power bi", "excel", "tieng anh", "html"} <= skills)
        self.assertNotIn("machine learning", skills)
        self.assertNotIn("java", skills)

    def test_extract_skills_uses_database_skill_names(self):
        extractor = get_extractor(("Ho tro CNTT", "Kế toán"))
        skills = extractor.extract("3 năm làm kế toán tổng hợp và hỗ trợ CNTT")
        self.assertEqual(extractor.names(skills), ["Hỗ trợ CNTT", "Kế toán"])

    def test_experience_from_explicit_sentence(self):
        self.assertEqual(parse_experience_years("Có hơn 3 năm kinh nghiệm lập trình Python"), 3.0)
        self.assertEqual(parse_experience_years("6 tháng kinh nghiệm thực tập"), 0.5)
        self.assertIsNone(parse_experience_years("Sinh viên năm 3 ngành Hệ thống thông tin"))

    def test_experience_from_section_ignores_education_dates(self):
        text = (
            "Kinh nghiệm làm việc\n01/2022 - 12/2023: Data Analyst tại ABC\n06/2024 - nay: BI Analyst tại XYZ\n"
            "Học vấn\n2016 - 2020: Đại học Bách Khoa"
        )
        self.assertEqual(parse_experience_years(text, today=date(2025, 6, 1)), 2.9)

    def test_education_level(self):
        self.assertEqual(parse_education_level("Thạc sĩ Khoa học dữ liệu, Cử nhân Đại học Kinh tế"), 4)
        self.assertEqual(parse_education_level("Cao đẳng hoặc Đại học", mode="min"), 2)
        self.assertEqual(parse_education_level("Chứng chỉ Scrum Master"), 0)

    def test_extract_text_from_docx_and_pdf(self):
        self.assertIn("Python", extract_text(make_docx("Kỹ năng", "Python, SQL"), "cv.docx"))
        self.assertIn("Power BI", extract_text(make_pdf("Data Analyst - SQL, Power BI"), "cv.pdf"))

    def test_unreadable_or_unsupported_file_returns_empty_text(self):
        with self.assertLogs(level="WARNING"):
            self.assertEqual(extract_text(b"not a pdf", "cv.pdf"), "")
        self.assertEqual(extract_text(b"binary", "cv.doc"), "")


class MatchingModelTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = MatchingModel.load(MODEL_PATH)
        cls.job = JobDoc(
            text="Data Analyst. Yêu cầu SQL, Power BI, Excel. Xây dựng dashboard và báo cáo phân tích dữ liệu.",
            title="Data Analyst",
            required_skills={"sql", "power bi", "excel"},
            preferred_skills={"python"},
            min_years=1,
            education_level=3,
            location="Hà Nội",
            work_mode="ONSITE",
            salary_min=12_000_000,
            salary_max=20_000_000,
        )

    def test_metrics_are_recorded_and_better_than_chance(self):
        metadata = self.model.metadata
        self.assertIn(metadata["model_name"], {"logistic_regression", "hist_gradient_boosting"})
        self.assertGreater(metadata["test_metrics"]["roc_auc"], 0.8)
        self.assertEqual(metadata["data_source"], "synthetic")

    def test_relevant_candidate_scores_higher_with_explanation(self):
        strong = CandidateDoc(
            text="Data Analyst 2 năm kinh nghiệm SQL, Power BI, Excel, Python. Xây dựng dashboard báo cáo phân tích dữ liệu.",
            title="Data Analyst",
            skills={"sql", "power bi", "excel", "python"},
            experience_years=2,
            education_level=3,
            location="TP. Hà Nội",
            desired_salary=15_000_000,
        )
        weak = CandidateDoc(
            text="Chuyên viên marketing số, SEO, Google Ads, viết content.",
            title="Digital Marketing",
            skills={"marketing so", "seo", "google ads"},
            experience_years=0,
            education_level=2,
            location="Đà Nẵng",
            desired_salary=30_000_000,
        )
        strong_result, weak_result = self.model.score(strong, self.job), self.model.score(weak, self.job)
        self.assertGreater(strong_result.score, weak_result.score + 30)
        self.assertTrue(0 <= weak_result.score <= strong_result.score <= 100)
        self.assertEqual(strong_result.explanation["required_skills"], "3/3")
        self.assertEqual(weak_result.explanation["missing_required_skills"], ["Excel", "Power BI", "SQL"])
        self.assertEqual(len(strong_result.explanation["top_factors"]), 4)

    def test_training_requires_both_labels(self):
        candidates, jobs, _ = generate_training_data(20, seed=1)
        with self.assertRaises(ValueError):
            train_matching_model(candidates, jobs, [1] * 20)


class MatchingIntegrationTests(TestCase):
    def setUp(self):
        # TEMP_DIR chỉ có sau setUpModule nên override trong setUp thay vì decorator lớp.
        settings_override = override_settings(MEDIA_ROOT=TEMP_DIR / "media", MATCHING_MODEL_PATH=MODEL_PATH)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        skills = {name: Skill.objects.create(name=name) for name in ["SQL", "Power BI", "Python", "Figma"]}
        employer_user = User.objects.create_user(username="hr", email="hr@example.com", password="StrongPass123", role=User.Role.EMPLOYER)
        self.employer = EmployerProfile.objects.create(user=employer_user, company_name="Data Co")
        self.job = Job.objects.create(
            employer=self.employer, title="Data Analyst", description="Phân tích dữ liệu, xây dựng dashboard Power BI.",
            requirements="SQL, Power BI", location="Hà Nội", status=Job.Status.OPEN, experience_level=Job.Experience.JUNIOR,
            deadline=timezone.localdate() + timedelta(days=10), salary_min=10_000_000, salary_max=20_000_000,
        )
        JobSkill.objects.create(job=self.job, skill=skills["SQL"], importance=JobSkill.Importance.REQUIRED)
        JobSkill.objects.create(job=self.job, skill=skills["Power BI"], importance=JobSkill.Importance.REQUIRED)
        JobSkill.objects.create(job=self.job, skill=skills["Python"], importance=JobSkill.Importance.PREFERRED)
        self.strong = self.make_candidate("strong", "Data Analyst", ["SQL", "Power BI", "Python"], skills)
        self.weak = self.make_candidate("weak", "Thiết kế đồ họa", ["Figma"], skills)

    def make_candidate(self, username, major, skill_names, skills):
        user = User.objects.create_user(username=username, email=f"{username}@example.com", password="StrongPass123", role=User.Role.CANDIDATE)
        profile = CandidateProfile.objects.create(user=user, major=major, location="Hà Nội", experience_years=2, desired_salary=15_000_000)
        for name in skill_names:
            CandidateSkill.objects.create(candidate=profile, skill=skills[name])
        return profile

    def test_apply_stores_ml_score_and_explanation(self):
        self.client.force_login(self.strong.user)
        self.client.post(reverse("application-apply", args=[self.job.pk]), {"cover_letter": "Quan tâm"})
        application = Application.objects.get(candidate=self.strong, job=self.job)
        self.assertIsNotNone(application.matching_score)
        self.assertEqual(application.matching_explanation["method"], "ml")
        self.assertEqual(application.matching_explanation["required_skills"], "2/2")

    def test_falls_back_to_rule_based_without_trained_model(self):
        with override_settings(MATCHING_MODEL_PATH=TEMP_DIR / "missing.joblib"):
            score, explanation = calculate_matching_score(self.strong, self.job)
        self.assertEqual(explanation["method"], "rule_based")
        self.assertGreater(score, 0)

    def test_resume_upload_is_parsed(self):
        self.client.force_login(self.weak.user)
        upload = SimpleUploadedFile("cv.docx", make_docx("Kinh nghiệm: 2 năm kinh nghiệm", "Kỹ năng: Python, SQL, Tableau"))
        self.client.post(reverse("candidate-profile"), {"resume_submit": "1", "file": upload})
        resume = Resume.objects.get(candidate=self.weak)
        self.assertIn("Tableau", resume.resume_text)
        self.assertEqual(resume.parsed_data["skills"], ["Python", "SQL", "Tableau"])
        self.assertEqual(resume.parsed_data["experience_years"], 2.0)
        self.assertTrue(resume.parsed_data["extracted_from_file"])

    def test_employer_sees_ranked_applicants_and_can_rescore(self):
        for candidate in (self.weak, self.strong):
            Application.objects.create(candidate=candidate, job=self.job)
        self.client.force_login(self.employer.user)
        url = reverse("employer-job-applicants", args=[self.job.pk])
        self.client.post(url)
        response = self.client.get(url)
        ranked = list(response.context["applications"])
        self.assertEqual([item.candidate for item in ranked], [self.strong, self.weak])
        self.assertGreater(ranked[0].matching_score, ranked[1].matching_score)

        other = User.objects.create_user(username="other", email="other@example.com", password="StrongPass123", role=User.Role.EMPLOYER)
        EmployerProfile.objects.create(user=other, company_name="Other Co")
        self.client.force_login(other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_job_detail_shows_match_preview_for_candidate(self):
        self.client.force_login(self.strong.user)
        response = self.client.get(reverse("job-detail", args=[self.job.pk]))
        self.assertEqual(response.context["match"]["explanation"]["method"], "ml")
        self.assertContains(response, "Độ phù hợp với hồ sơ của bạn")

    def test_train_command_writes_model_and_report(self):
        output = TEMP_DIR / "command" / "model.joblib"
        call_command("train_matching_model", samples=300, output=str(output), stdout=io.StringIO())
        self.assertTrue(output.exists())
        self.assertTrue(output.with_suffix(".json").exists())
