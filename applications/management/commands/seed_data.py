from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from applications.models import Application
from candidates.models import CandidateProfile, CandidateSkill, Resume
from employers.models import EmployerProfile
from jobs.models import Job, JobSkill, Skill


PDF_SAMPLE = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]/Contents 4 0 R/Resources<<>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 14 Tf 40 130 Td (Smart Recruitment CV) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f
trailer<</Size 5/Root 1 0 R>>
startxref
0
%%EOF
"""


class Command(BaseCommand):
    help = "Tao du lieu mau tieng Viet, idempotent va an toan cho moi truong phat trien."

    skill_data = [
        ("SQL", "Phân tích dữ liệu"),
        ("Excel", "Phân tích dữ liệu"),
        ("Python", "Lập trình"),
        ("Power BI", "Phân tích dữ liệu"),
        ("Tableau", "Phân tích dữ liệu"),
        ("HTML", "Frontend"),
        ("CSS", "Frontend"),
        ("JavaScript", "Frontend"),
        ("React", "Frontend"),
        ("Django", "Backend"),
        ("Git", "Công cụ"),
        ("Giao tiếp", "Kỹ năng mềm"),
        ("Phân tích nghiệp vụ", "Business"),
        ("Tư duy logic", "Kỹ năng mềm"),
        ("Java", "Lập trình"),
        ("Figma", "Thiết kế"),
        ("Jira", "Quản lý dự án"),
        ("Kiểm thử phần mềm", "QA"),
        ("Tiếng Anh", "Ngoại ngữ"),
        ("Marketing số", "Marketing"),
    ]

    employer_data = [
        {
            "username": "demo_employer_techcom",
            "email": "techcom@demo.smartrecruitment.local",
            "company_name": "Công ty Công nghệ TechCom",
            "industry": "Công nghệ thông tin",
            "address": "Tòa nhà Etown, Tân Bình, TP. Hồ Chí Minh",
            "website": "https://example.com/techcom",
            "description": "TechCom phát triển nền tảng số và sản phẩm phần mềm cho doanh nghiệp Việt Nam.",
        },
        {
            "username": "demo_employer_vietdata",
            "email": "vietdata@demo.smartrecruitment.local",
            "company_name": "VietData Analytics",
            "industry": "Dữ liệu và tư vấn",
            "address": "Quận Cầu Giấy, Hà Nội",
            "website": "https://example.com/vietdata",
            "description": "VietData cung cấp giải pháp phân tích dữ liệu, báo cáo BI và tư vấn chuyển đổi số.",
        },
        {
            "username": "demo_employer_growplus",
            "email": "growplus@demo.smartrecruitment.local",
            "company_name": "GrowPlus Media",
            "industry": "Marketing và truyền thông",
            "address": "Quận Hải Châu, Đà Nẵng",
            "website": "https://example.com/growplus",
            "description": "GrowPlus xây dựng chiến dịch marketing số giúp thương hiệu tiếp cận khách hàng trẻ.",
        },
    ]

    candidate_data = [
        ("Nguyễn Minh Anh", "minhanh01@demo.smartrecruitment.local", "0901000001", "Đại học Kinh tế TP. Hồ Chí Minh", "TP. Hồ Chí Minh", "Sinh viên năm cuối yêu thích phân tích dữ liệu và trực quan hóa báo cáo."),
        ("Trần Hoàng Nam", "hoangnam02@demo.smartrecruitment.local", "0901000002", "Đại học Bách khoa Hà Nội", "Hà Nội", "Lập trình viên mới tốt nghiệp, chủ động học hỏi và thích xây dựng sản phẩm web."),
        ("Lê Ngọc Hà", "ngocha03@demo.smartrecruitment.local", "0901000003", "Đại học Ngoại thương", "Hà Nội", "Ứng viên Business Analyst có tư duy hệ thống và khả năng giao tiếp tốt."),
        ("Phạm Quốc Bảo", "quocbao04@demo.smartrecruitment.local", "0901000004", "Đại học Công nghệ TP. Hồ Chí Minh", "TP. Hồ Chí Minh", "Đam mê phát triển frontend và trải nghiệm người dùng."),
        ("Võ Thùy Linh", "thuylinh05@demo.smartrecruitment.local", "0901000005", "Đại học Kinh tế Đà Nẵng", "Đà Nẵng", "Quan tâm đến marketing số, nội dung sáng tạo và tăng trưởng thương hiệu."),
        ("Đỗ Gia Huy", "giahuy06@demo.smartrecruitment.local", "0901000006", "Đại học FPT", "Đà Nẵng", "Có nền tảng Python, Django và SQL, mong muốn phát triển backend."),
        ("Nguyễn Khánh Vy", "khanhvy07@demo.smartrecruitment.local", "0901000007", "Đại học Thương mại", "Hà Nội", "Yêu thích nghiên cứu thị trường và phân tích hành vi khách hàng."),
        ("Bùi Đức Anh", "ducanh08@demo.smartrecruitment.local", "0901000008", "Đại học Khoa học Tự nhiên", "TP. Hồ Chí Minh", "Sinh viên ngành khoa học máy tính, mạnh về tư duy logic và Git."),
        ("Phan Mai Chi", "maichi09@demo.smartrecruitment.local", "0901000009", "Đại học RMIT Việt Nam", "TP. Hồ Chí Minh", "Có khả năng làm việc bằng tiếng Anh và trình bày dữ liệu rõ ràng."),
        ("Hoàng Tuấn Kiệt", "tuankiet10@demo.smartrecruitment.local", "0901000010", "Đại học Duy Tân", "Đà Nẵng", "Quan tâm đến kiểm thử phần mềm và đảm bảo chất lượng sản phẩm."),
        ("Đặng Ngọc Mai", "ngocmai11@demo.smartrecruitment.local", "0901000011", "Đại học Lao động - Xã hội", "Hà Nội", "Năng động, cẩn thận và có hứng thú với nghiệp vụ nhân sự."),
        ("Trương Nhật Minh", "nhatminh12@demo.smartrecruitment.local", "0901000012", "Đại học Sư phạm Kỹ thuật", "TP. Hồ Chí Minh", "Thích giải quyết vấn đề bằng code và làm việc theo quy trình Agile."),
        ("Hồ Thanh Tâm", "thanhtam13@demo.smartrecruitment.local", "0901000013", "Đại học Kinh tế Quốc dân", "Hà Nội", "Có định hướng phát triển trong lĩnh vực BI và quản trị kinh doanh."),
        ("Mai Phương Thảo", "phuongthao14@demo.smartrecruitment.local", "0901000014", "Đại học Văn Lang", "TP. Hồ Chí Minh", "Quan tâm đến thiết kế giao diện, Figma và nghiên cứu người dùng."),
        ("Nguyễn Thành Đạt", "thanhdat15@demo.smartrecruitment.local", "0901000015", "Đại học Bách khoa Đà Nẵng", "Đà Nẵng", "Kỹ sư trẻ yêu thích Java, kiểm thử và phát triển phần mềm bền vững."),
    ]

    job_titles = [
        ("Business Analyst Intern", "Phân tích nghiệp vụ", Job.JobType.INTERNSHIP, Job.Experience.ENTRY),
        ("Junior Business Analyst", "Phân tích nghiệp vụ", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
        ("Business Analyst - Sản phẩm số", "Phân tích nghiệp vụ", Job.JobType.FULL_TIME, Job.Experience.MID),
        ("Data Analyst Intern", "Phân tích dữ liệu", Job.JobType.INTERNSHIP, Job.Experience.ENTRY),
        ("Data Analyst - Marketing", "Phân tích dữ liệu", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
        ("Data Analyst", "Phân tích dữ liệu", Job.JobType.FULL_TIME, Job.Experience.MID),
        ("BI Analyst", "Business Intelligence", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
        ("Power BI Developer", "Business Intelligence", Job.JobType.FULL_TIME, Job.Experience.MID),
        ("BI Reporting Intern", "Business Intelligence", Job.JobType.INTERNSHIP, Job.Experience.ENTRY),
        ("Software Developer Intern", "Phát triển phần mềm", Job.JobType.INTERNSHIP, Job.Experience.ENTRY),
        ("Junior Software Developer", "Phát triển phần mềm", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
        ("Software Developer - Java", "Phát triển phần mềm", Job.JobType.FULL_TIME, Job.Experience.MID),
        ("Frontend Developer Intern", "Phát triển phần mềm", Job.JobType.INTERNSHIP, Job.Experience.ENTRY),
        ("Junior Frontend Developer", "Phát triển phần mềm", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
        ("Frontend Developer - React", "Phát triển phần mềm", Job.JobType.FULL_TIME, Job.Experience.MID),
        ("Backend Developer Intern", "Phát triển phần mềm", Job.JobType.INTERNSHIP, Job.Experience.ENTRY),
        ("Junior Backend Developer", "Phát triển phần mềm", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
        ("Backend Developer - Django", "Phát triển phần mềm", Job.JobType.FULL_TIME, Job.Experience.MID),
        ("Software Tester Intern", "Kiểm thử phần mềm", Job.JobType.INTERNSHIP, Job.Experience.ENTRY),
        ("Manual Tester", "Kiểm thử phần mềm", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
        ("QA Tester", "Kiểm thử phần mềm", Job.JobType.FULL_TIME, Job.Experience.MID),
        ("Digital Marketing Intern", "Marketing số", Job.JobType.INTERNSHIP, Job.Experience.ENTRY),
        ("Digital Marketing Executive", "Marketing số", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
        ("SEO Content Specialist", "Marketing số", Job.JobType.FULL_TIME, Job.Experience.MID),
        ("Business Intelligence Intern", "Business Intelligence", Job.JobType.INTERNSHIP, Job.Experience.ENTRY),
        ("Business Intelligence Consultant", "Business Intelligence", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
        ("BI Data Visualization Specialist", "Business Intelligence", Job.JobType.FULL_TIME, Job.Experience.MID),
        ("Full-stack Developer", "Phát triển phần mềm", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
        ("Product Data Analyst", "Phân tích dữ liệu", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
        ("Business Process Analyst", "Phân tích nghiệp vụ", Job.JobType.FULL_TIME, Job.Experience.JUNIOR),
    ]

    def _upsert_user(self, username, email, role, first_name="", last_name=""):
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
        today = timezone.localdate()
        counts = {"users_created": 0, "profiles_created": 0, "skills_created": 0, "jobs_created": 0, "applications_created": 0, "resumes_created": 0}

        skills = []
        for name, category in self.skill_data:
            skill, created = Skill.objects.get_or_create(name=name, defaults={"category": category})
            if skill.category != category:
                skill.category = category
                skill.save(update_fields=["category"])
            skills.append(skill)
            counts["skills_created"] += int(created)

        employers = []
        for item in self.employer_data:
            user, created = self._upsert_user(item["username"], item["email"], User.Role.EMPLOYER, item["company_name"])
            counts["users_created"] += int(created)
            profile, profile_created = EmployerProfile.objects.update_or_create(user=user, defaults={key: item[key] for key in ("company_name", "industry", "address", "website", "description")})
            employers.append(profile)
            counts["profiles_created"] += int(profile_created)

        candidates = []
        for index, (full_name, email, phone, education, location, bio) in enumerate(self.candidate_data, start=1):
            first_name, last_name = full_name.split(" ", 1)
            user, created = self._upsert_user(f"demo_candidate_{index:02d}", email, User.Role.CANDIDATE, first_name, last_name)
            counts["users_created"] += int(created)
            profile, profile_created = CandidateProfile.objects.update_or_create(
                user=user,
                defaults={"phone": phone, "date_of_birth": date(2000 + index % 5, (index % 12) + 1, (index % 27) + 1), "education": education, "location": location, "bio": bio},
            )
            candidates.append(profile)
            counts["profiles_created"] += int(profile_created)

        candidate_skill_sets = [
            [0, 1, 3, 11], [2, 9, 10, 13], [0, 1, 12, 13], [5, 6, 7, 8],
            [15, 19, 11, 18], [2, 9, 0, 10], [1, 3, 4, 12], [2, 10, 13, 16],
            [3, 4, 18, 11], [17, 10, 13, 18], [1, 6, 11, 12], [2, 9, 10, 13],
            [0, 3, 4, 12], [15, 5, 6, 11], [14, 17, 10, 13],
        ]
        for candidate, skill_indexes in zip(candidates, candidate_skill_sets):
            for skill_index in skill_indexes:
                CandidateSkill.objects.update_or_create(
                    candidate=candidate,
                    skill=skills[skill_index],
                    defaults={"proficiency_level": "Khá" if skill_index % 2 else "Tốt"},
                )

        jobs = []
        for index, (title, category, job_type, experience) in enumerate(self.job_titles):
            employer = employers[index % len(employers)]
            status = Job.Status.OPEN if index < 26 else (Job.Status.CLOSED if index < 28 else Job.Status.DRAFT)
            job, created = Job.objects.update_or_create(
                employer=employer,
                title=title,
                defaults={
                    "description": f"Tham gia đội ngũ {employer.company_name} để xây dựng các giải pháp {category.lower()} có tác động thực tế.",
                    "requirements": "Sinh viên năm cuối hoặc mới tốt nghiệp; có tinh thần học hỏi, tư duy logic và khả năng làm việc nhóm.",
                    "responsibilities": "Phối hợp với các thành viên, thực hiện công việc theo kế hoạch và trình bày kết quả rõ ràng.",
                    "location": ["TP. Hồ Chí Minh", "Hà Nội", "Đà Nẵng"][index % 3],
                    "job_type": job_type,
                    "salary_min": 4_000_000 + (index % 5) * 2_000_000,
                    "salary_max": 8_000_000 + (index % 5) * 3_000_000,
                    "experience_level": experience,
                    "status": status,
                    "deadline": today + timedelta(days=30 + index),
                },
            )
            job.full_clean()
            jobs.append(job)
            counts["jobs_created"] += int(created)
            skill_indexes = [(index + offset) % len(skills) for offset in range(4)]
            for offset, skill_index in enumerate(skill_indexes):
                JobSkill.objects.update_or_create(
                    job=job,
                    skill=skills[skill_index],
                    defaults={"importance": JobSkill.Importance.REQUIRED if offset < 2 else JobSkill.Importance.PREFERRED},
                )

        for index, candidate in enumerate(candidates):
            resume, created = Resume.objects.get_or_create(candidate=candidate, original_filename=f"CV-demo-{index + 1:02d}.pdf")
            if created:
                resume.file.save(resume.original_filename, ContentFile(PDF_SAMPLE), save=True)
            counts["resumes_created"] += int(created)

        statuses = [Application.Status.APPLIED, Application.Status.REVIEWING, Application.Status.INTERVIEW, Application.Status.ACCEPTED, Application.Status.REJECTED]
        for index in range(20):
            candidate = candidates[index % len(candidates)]
            job = jobs[index]
            resume = candidate.resumes.first()
            application, created = Application.objects.get_or_create(
                candidate=candidate,
                job=job,
                defaults={"resume": resume, "status": statuses[index % len(statuses)], "cover_letter": "Tôi tin rằng kỹ năng và tinh thần học hỏi của mình phù hợp với vị trí này."},
            )
            if not created and application.status != statuses[index % len(statuses)]:
                application.status = statuses[index % len(statuses)]
                application.save(update_fields=["status"])
            counts["applications_created"] += int(created)

        self.stdout.write(self.style.SUCCESS("Smart Recruitment sample data loaded."))
        self.stdout.write(" | ".join(f"{key}={value}" for key, value in counts.items()))
        self.stdout.write(
            f"Current totals: users={User.objects.count()}, employers={EmployerProfile.objects.count()}, "
            f"candidates={CandidateProfile.objects.count()}, skills={Skill.objects.count()}, jobs={Job.objects.count()}, "
            f"resumes={Resume.objects.count()}, applications={Application.objects.count()}"
        )
