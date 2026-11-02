from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from applications.matching import calculate_matching_score
from applications.models import Application
from candidates.models import CandidateProfile, CandidateSkill, Resume
from employers.models import EmployerProfile
from jobs.models import Job, JobSkill, Skill


PDF_SAMPLE = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


class Command(BaseCommand):
    help = "Tao bo du lieu demo quy mo lon cho AI matching va BI."

    skills = [
        ("SQL", "Data"), ("Excel", "Data"), ("Python", "Data"), ("Power BI", "BI"),
        ("Tableau", "BI"), ("HTML", "Frontend"), ("CSS", "Frontend"),
        ("JavaScript", "Frontend"), ("React", "Frontend"), ("Django", "Backend"),
        ("Git", "Tools"), ("Giao tiep", "Soft skills"), ("Phan tich nghiep vu", "Business"),
        ("Tu duy logic", "Soft skills"), ("Java", "Backend"), ("Figma", "Design"),
        ("Jira", "Tools"), ("Kiem thu phan mem", "QA"), ("Tieng Anh", "Language"),
        ("Ho tro CNTT", "IT Support"),
    ]
    first_names = ["Nguyen", "Tran", "Le", "Pham", "Vo", "Do", "Bui", "Hoang", "Dang", "Phan"]
    given_names = ["Minh Anh", "Hoang Nam", "Ngoc Ha", "Quoc Bao", "Thuy Linh", "Gia Huy", "Khanh Vy", "Duc Anh", "Mai Chi", "Tuan Kiet"]
    directions = [
        ("Business Analyst", ["SQL", "Excel", "Phan tich nghiep vu", "Giao tiep"]),
        ("Data Analyst", ["SQL", "Excel", "Python", "Power BI"]),
        ("Software Developer", ["Python", "Git", "Tu duy logic", "Tieng Anh"]),
        ("Frontend Developer", ["HTML", "CSS", "JavaScript", "React"]),
        ("Backend Developer", ["Python", "Django", "SQL", "Git"]),
        ("QA Tester", ["Kiem thu phan mem", "Jira", "SQL", "Tu duy logic"]),
        ("UI/UX Designer", ["Figma", "Giao tiep", "Tu duy logic", "Tieng Anh"]),
        ("IT Support", ["Ho tro CNTT", "Giao tiep", "Git", "Tieng Anh"]),
        ("BI Analyst", ["Power BI", "Tableau", "SQL", "Excel"]),
        ("Data Engineer", ["Python", "SQL", "Git", "Tu duy logic"]),
    ]

    def upsert_user(self, username, email, role, first_name, last_name=""):
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.role = role
        user.first_name = first_name
        user.last_name = last_name
        user.set_unusable_password()
        user.save(update_fields=["email", "role", "first_name", "last_name", "password"])
        return user, created

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        counts = {"users": 0, "employers": 0, "candidates": 0, "skills": 0, "jobs": 0, "resumes": 0, "candidate_skills": 0, "job_skills": 0, "applications": 0}
        skill_map = {}
        for name, category in self.skills:
            skill, created = Skill.objects.get_or_create(name=name, defaults={"category": category})
            skill_map[name] = skill
            counts["skills"] += int(created)

        employers = []
        for index in range(1, 21):
            user, created = self.upsert_user(f"scale_employer_{index:02d}", f"company{index:02d}@demo.smartrecruitment.local", User.Role.EMPLOYER, f"Cong ty Demo {index:02d}")
            counts["users"] += int(created)
            profile, profile_created = EmployerProfile.objects.update_or_create(
                user=user,
                defaults={
                    "company_name": f"Công ty Demo {index:02d}",
                    "industry": ["Công nghệ thông tin", "Dữ liệu và BI", "Thương mại điện tử", "Marketing số"][index % 4],
                    "address": ["TP. Hồ Chí Minh", "Hà Nội", "Đà Nẵng"][index % 3],
                    "website": f"https://demo-company-{index:02d}.example.com",
                    "description": "Doanh nghiệp giả lập phục vụ kiểm thử nền tảng tuyển dụng và báo cáo BI.",
                },
            )
            employers.append(profile)
            counts["employers"] += int(profile_created)

        candidates = []
        for index in range(1, 101):
            family = self.first_names[(index - 1) % len(self.first_names)]
            given = self.given_names[(index - 1) % len(self.given_names)]
            direction, _ = self.directions[(index - 1) % len(self.directions)]
            user, created = self.upsert_user(f"scale_candidate_{index:03d}", f"candidate{index:03d}@demo.smartrecruitment.local", User.Role.CANDIDATE, f"{family} {given}")
            counts["users"] += int(created)
            profile, profile_created = CandidateProfile.objects.update_or_create(
                user=user,
                defaults={
                    "phone": f"09{index:08d}",
                    "location": ["TP. Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Cần Thơ"][index % 4],
                    "education": f"Đại học Demo Việt Nam - ngành {direction}",
                    "major": direction,
                    "year_of_study": (index % 4) + 1,
                    "experience_years": Decimal(str((index % 7) / 2)),
                    "desired_salary": 7_000_000 + (index % 8) * 2_000_000,
                    "bio": f"Ứng viên giả lập định hướng {direction}, chủ động học hỏi và yêu thích giải quyết vấn đề.",
                    "projects": f"Dự án cá nhân {direction} Demo: phân tích yêu cầu, xây dựng sản phẩm thử nghiệm và trình bày kết quả.",
                },
            )
            candidates.append(profile)
            counts["candidates"] += int(profile_created)
            resume, resume_created = Resume.objects.get_or_create(candidate=profile, original_filename=f"CV-scale-{index:03d}.pdf")
            if resume_created:
                resume.resume_text = f"CV giả lập {given}. Định hướng {direction}. Kỹ năng: {', '.join(self.directions[(index - 1) % len(self.directions)][1])}."
                resume.file.save(resume.original_filename, ContentFile(PDF_SAMPLE), save=True)
            counts["resumes"] += int(resume_created)
            skill_names = self.directions[(index - 1) % len(self.directions)][1]
            for offset in range(5):
                skill = skill_map[skill_names[offset % len(skill_names)]] if offset < len(skill_names) else list(skill_map.values())[(index + offset) % len(skill_map)]
                _, relation_created = CandidateSkill.objects.update_or_create(
                    candidate=profile,
                    skill=skill,
                    defaults={"proficiency_level": ["Cơ bản", "Khá", "Tốt"][index % 3], "experience_years": Decimal(str((index % 5) / 2))},
                )
                counts["candidate_skills"] += int(relation_created)

        jobs = []
        for index in range(1, 51):
            direction, required_names = self.directions[(index - 1) % len(self.directions)]
            suffix = ["Intern", "Junior", "Specialist", "Engineer", "Lead"][index % 5]
            title = f"{direction} {suffix} - Demo {index:02d}"
            status = Job.Status.OPEN if index <= 42 else (Job.Status.CLOSED if index <= 46 else Job.Status.DRAFT)
            job, created = Job.objects.update_or_create(
                employer=employers[(index - 1) % len(employers)],
                title=title,
                defaults={
                    "description": f"Tham gia dự án thực tế về {direction}, phối hợp với đội ngũ đa chức năng và tạo ra kết quả đo lường được.",
                    "requirements": f"Có nền tảng {direction}, tư duy logic, giao tiếp tốt và sẵn sàng học công nghệ mới.",
                    "responsibilities": "Phân tích yêu cầu, thực hiện nhiệm vụ theo sprint, kiểm tra chất lượng và báo cáo tiến độ.",
                    "location": ["TP. Hồ Chí Minh", "Hà Nội", "Đà Nẵng"][index % 3],
                    "work_mode": [Job.WorkMode.ONSITE, Job.WorkMode.HYBRID, Job.WorkMode.REMOTE][index % 3],
                    "job_type": Job.JobType.INTERNSHIP if index % 5 == 1 else Job.JobType.FULL_TIME,
                    "education_level": "Cao đẳng hoặc Đại học",
                    "openings": (index % 5) + 1,
                    "salary_min": 5_000_000 + (index % 8) * 2_000_000,
                    "salary_max": 10_000_000 + (index % 8) * 3_000_000,
                    "experience_level": [Job.Experience.ENTRY, Job.Experience.JUNIOR, Job.Experience.MID][index % 3],
                    "status": status,
                    "deadline": (now + timedelta(days=30 + index)).date(),
                },
            )
            job.created_at = now - timedelta(days=(index * 7) % 540)
            job.updated_at = job.created_at
            job.save(update_fields=["created_at", "updated_at"])
            jobs.append(job)
            counts["jobs"] += int(created)
            for offset, skill_name in enumerate(required_names):
                _, relation_created = JobSkill.objects.update_or_create(
                    job=job,
                    skill=skill_map[skill_name],
                    defaults={"importance": JobSkill.Importance.REQUIRED if offset < 2 else JobSkill.Importance.PREFERRED, "minimum_years": Decimal(str((index % 4) / 2))},
                )
                counts["job_skills"] += int(relation_created)

        open_jobs = jobs[:42]
        statuses = [Application.Status.APPLIED, Application.Status.REVIEWING, Application.Status.INTERVIEW, Application.Status.ACCEPTED, Application.Status.REJECTED, Application.Status.WITHDRAWN]
        for index in range(200):
            candidate = candidates[index % 100]
            job = open_jobs[index % len(open_jobs)]
            application, created = Application.objects.get_or_create(candidate=candidate, job=job)
            score, explanation = calculate_matching_score(candidate, job)
            application.resume = candidate.resumes.first()
            application.status = statuses[index % len(statuses)]
            application.cover_letter = "Tôi quan tâm đến vị trí này và mong muốn được trao đổi thêm về sự phù hợp."
            application.matching_score = score
            application.matching_explanation = explanation
            application.save()
            application.applied_at = now - timedelta(days=(index * 3) % 365)
            application.save(update_fields=["applied_at"])
            counts["applications"] += int(created)

        self.stdout.write(self.style.SUCCESS("Demo data loaded successfully."))
        self.stdout.write("Created relations: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
        self.stdout.write(
            f"Totals: users={User.objects.count()}, employers={EmployerProfile.objects.count()}, candidates={CandidateProfile.objects.count()}, "
            f"skills={Skill.objects.count()}, jobs={Job.objects.count()}, resumes={Resume.objects.count()}, applications={Application.objects.count()}"
        )
