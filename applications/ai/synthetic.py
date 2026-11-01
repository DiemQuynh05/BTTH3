"""Sinh dữ liệu huấn luyện mô phỏng (cold-start) khi chưa có kết quả tuyển dụng thực tế.

Nhãn được sinh từ một hàm quyết định ẩn của "nhà tuyển dụng" dựa trên thông tin
thật của ứng viên (kỹ năng thật, vai trò thật, kinh nghiệm thật) cộng nhiễu, còn
mô hình chỉ nhìn thấy những gì trích xuất được từ văn bản CV/JD. Kết quả đánh giá
trên dữ liệu này chỉ chứng minh pipeline hoạt động, không thay thế đánh giá trên
dữ liệu tuyển dụng thực.
"""
from datetime import date

import numpy as np

from .cv_parser import parse_education_level, parse_experience_years
from .features import LEVEL_MIN_YEARS, CandidateDoc, JobDoc
from .skills import SKILL_TAXONOMY, get_extractor

ROLES = {
    "data_analyst": {
        "titles": ("Data Analyst", "Chuyên viên phân tích dữ liệu"),
        "core": ("SQL", "Excel", "Python", "Power BI"),
        "secondary": ("Tableau", "Thống kê", "Tiếng Anh", "Tư duy logic"),
        "keywords": ("phân tích dữ liệu", "báo cáo định kỳ", "dashboard", "trực quan hóa dữ liệu", "chỉ số KPI", "làm sạch dữ liệu"),
    },
    "bi_analyst": {
        "titles": ("BI Analyst", "Chuyên viên Business Intelligence"),
        "core": ("Power BI", "SQL", "Tableau", "Excel"),
        "secondary": ("ETL", "Python", "Giao tiếp", "Tiếng Anh"),
        "keywords": ("mô hình dữ liệu", "data mart", "dashboard quản trị", "báo cáo BI", "chỉ số KPI", "kho dữ liệu"),
    },
    "business_analyst": {
        "titles": ("Business Analyst", "Chuyên viên phân tích nghiệp vụ"),
        "core": ("Phân tích nghiệp vụ", "SQL", "Excel", "Giao tiếp"),
        "secondary": ("Jira", "UML", "Agile", "Tiếng Anh"),
        "keywords": ("thu thập yêu cầu", "user story", "quy trình nghiệp vụ", "tài liệu đặc tả", "làm việc với khách hàng"),
    },
    "data_engineer": {
        "titles": ("Data Engineer", "Kỹ sư dữ liệu"),
        "core": ("Python", "SQL", "Spark", "Airflow"),
        "secondary": ("Docker", "AWS", "Git", "PostgreSQL"),
        "keywords": ("xây dựng data pipeline", "kho dữ liệu", "data lake", "xử lý dữ liệu lớn", "tối ưu truy vấn"),
    },
    "data_scientist": {
        "titles": ("Data Scientist", "Kỹ sư Machine Learning"),
        "core": ("Python", "Machine Learning", "Thống kê", "SQL"),
        "secondary": ("Deep Learning", "Pandas", "Git", "Tiếng Anh"),
        "keywords": ("mô hình dự đoán", "feature engineering", "bài toán phân loại", "đánh giá mô hình", "phân tích dữ liệu"),
    },
    "backend_developer": {
        "titles": ("Backend Developer", "Lập trình viên Backend Python"),
        "core": ("Python", "Django", "SQL", "Git"),
        "secondary": ("Docker", "REST API", "PostgreSQL", "Linux"),
        "keywords": ("phát triển API", "cơ sở dữ liệu", "tối ưu hiệu năng", "kiến trúc hệ thống", "phát triển web"),
    },
    "java_developer": {
        "titles": ("Java Developer", "Lập trình viên Java"),
        "core": ("Java", "Spring Boot", "SQL", "Git"),
        "secondary": ("Docker", "REST API", "Linux", "MySQL"),
        "keywords": ("phát triển API", "microservice", "hệ thống doanh nghiệp", "tối ưu hiệu năng", "phát triển web"),
    },
    "frontend_developer": {
        "titles": ("Frontend Developer", "Lập trình viên Frontend"),
        "core": ("HTML", "CSS", "JavaScript", "React"),
        "secondary": ("TypeScript", "Git", "Figma", "Tiếng Anh"),
        "keywords": ("xây dựng giao diện", "responsive", "single page application", "tối ưu trải nghiệm", "phát triển web"),
    },
    "qa_tester": {
        "titles": ("QA Tester", "Kỹ sư kiểm thử phần mềm"),
        "core": ("Kiểm thử phần mềm", "Jira", "SQL", "Selenium"),
        "secondary": ("Tư duy logic", "Tiếng Anh", "Git", "Agile"),
        "keywords": ("viết test case", "kiểm thử hồi quy", "báo cáo lỗi", "đảm bảo chất lượng", "quy trình phát hành"),
    },
    "uiux_designer": {
        "titles": ("UI/UX Designer", "Nhà thiết kế UI/UX"),
        "core": ("Figma", "UI/UX", "Photoshop", "Giao tiếp"),
        "secondary": ("HTML", "CSS", "Tiếng Anh", "Tư duy logic"),
        "keywords": ("wireframe", "prototype", "nghiên cứu người dùng", "design system", "trải nghiệm người dùng"),
    },
    "it_support": {
        "titles": ("IT Support", "Chuyên viên hỗ trợ kỹ thuật"),
        "core": ("Hỗ trợ CNTT", "Linux", "Mạng máy tính", "Giao tiếp"),
        "secondary": ("Windows Server", "Tiếng Anh", "Excel", "Git"),
        "keywords": ("xử lý sự cố", "cài đặt phần mềm", "bảo trì phần cứng", "quản trị hệ thống", "hỗ trợ người dùng"),
    },
    "digital_marketing": {
        "titles": ("Digital Marketing Executive", "Chuyên viên Marketing số"),
        "core": ("Marketing số", "SEO", "Google Ads", "Content Marketing"),
        "secondary": ("Excel", "Giao tiếp", "Tiếng Anh", "Photoshop"),
        "keywords": ("chiến dịch quảng cáo", "mạng xã hội", "tỷ lệ chuyển đổi", "xây dựng thương hiệu", "phân tích thị trường"),
    },
}
CITIES = ("TP. Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Cần Thơ", "Hải Phòng")
LEVELS = ("ENTRY", "JUNIOR", "MID", "SENIOR")
LEVEL_SALARY = {"ENTRY": 8_000_000, "JUNIOR": 14_000_000, "MID": 24_000_000, "SENIOR": 38_000_000}
LEVEL_SUFFIX = {"ENTRY": "Intern", "JUNIOR": "Junior", "MID": "", "SENIOR": "Senior"}
EDUCATION_TEXT = {
    1: "Tốt nghiệp THPT, tự học qua các khóa học trực tuyến",
    2: "Cao đẳng Công nghệ thông tin",
    3: "Cử nhân Đại học",
    4: "Thạc sĩ",
}
JOB_EDUCATION_TEXT = {0: "", 2: "Tốt nghiệp Cao đẳng hoặc Đại học.", 3: "Tốt nghiệp Đại học chuyên ngành liên quan."}


def _role_similarity():
    skills = {name: set(role["core"]) | set(role["secondary"]) for name, role in ROLES.items()}
    adjacent = {}
    for name, own in skills.items():
        ranked = sorted((len(own & other) / len(own | other), other_name) for other_name, other in skills.items() if other_name != name)
        adjacent[name] = [other_name for _, other_name in ranked[-2:]]
    return adjacent


ADJACENT_ROLES = _role_similarity()


def _mention(rng, skill):
    """Viết tên kỹ năng theo một biến thể ngẫu nhiên để mô phỏng cách ghi khác nhau trong CV."""
    aliases = SKILL_TAXONOMY.get(skill, ())
    if aliases and rng.random() < 0.35:
        return str(rng.choice(aliases))
    return skill


def _sample(rng, items, k):
    k = max(0, min(k, len(items)))
    return [items[i] for i in rng.choice(len(items), size=k, replace=False)]


def _months_ago(today, months):
    total = today.year * 12 + today.month - 1 - months
    return total // 12, total % 12 + 1


def _make_job(rng, today):
    role_name = str(rng.choice(list(ROLES)))
    role = ROLES[role_name]
    level = str(rng.choice(LEVELS, p=[0.35, 0.3, 0.25, 0.1]))
    required = _sample(rng, list(role["core"]), int(rng.integers(2, 5)))
    preferred = _sample(rng, [s for s in (*role["core"], *role["secondary"]) if s not in required], int(rng.integers(1, 4)))
    min_years = LEVEL_MIN_YEARS[level]
    education = int(rng.choice([0, 2, 3], p=[0.25, 0.4, 0.35]))
    base_salary = LEVEL_SALARY[level] * rng.uniform(0.8, 1.2)
    title = f"{rng.choice(role['titles'])} {LEVEL_SUFFIX[level]}".strip()
    keywords = _sample(rng, list(role["keywords"]), 3)
    experience_text = "Không yêu cầu kinh nghiệm, chào đón sinh viên mới tốt nghiệp." if not min_years else f"Có tối thiểu {min_years:g} năm kinh nghiệm ở vị trí tương đương."
    text = (
        f"{title}\n"
        f"Mô tả công việc: Tham gia {keywords[0]} và {keywords[1]}, phối hợp với các nhóm liên quan trong mảng {keywords[2]}.\n"
        f"Yêu cầu: Thành thạo {', '.join(_mention(rng, s) for s in required)}. {experience_text} {JOB_EDUCATION_TEXT[education]}\n"
        f"Ưu tiên ứng viên biết {', '.join(_mention(rng, s) for s in preferred)}."
    )
    extractor = get_extractor()
    work_mode = str(rng.choice(["ONSITE", "HYBRID", "REMOTE"], p=[0.5, 0.3, 0.2]))
    job = JobDoc(
        text=text,
        title=title,
        required_skills={extractor.key(s) for s in required},
        preferred_skills={extractor.key(s) for s in preferred},
        min_years=min_years,
        education_level=parse_education_level(JOB_EDUCATION_TEXT[education], mode="min"),
        location=str(rng.choice(CITIES)),
        work_mode=work_mode,
        salary_min=round(base_salary * 0.8, -5),
        salary_max=round(base_salary * 1.25, -5),
    )
    return role_name, level, education, job


def _make_candidate(rng, job_role, job, today):
    draw = rng.random()
    if draw < 0.45:
        role_name, relevance = job_role, 1.0
    elif draw < 0.75:
        role_name, relevance = str(rng.choice(ADJACENT_ROLES[job_role])), 0.5
    else:
        role_name = str(rng.choice([name for name in ROLES if name != job_role]))
        relevance = 0.5 if role_name in ADJACENT_ROLES[job_role] else 0.0
    role = ROLES[role_name]
    true_skills = [s for s in role["core"] if rng.random() < 0.75] + [s for s in role["secondary"] if rng.random() < 0.4]
    all_skills = list(SKILL_TAXONOMY)
    true_skills += _sample(rng, [s for s in all_skills if s not in true_skills], int(rng.integers(0, 3)))
    years = float(np.clip(np.round(rng.gamma(1.6, 1.6) * 2) / 2, 0, 15))
    education = int(rng.choice([1, 2, 3, 4], p=[0.05, 0.2, 0.65, 0.1]))
    location = job.location if rng.random() < 0.5 else str(rng.choice(CITIES))
    desired_salary = round(7_000_000 * (1 + 0.28 * years) * rng.lognormal(0, 0.18), -5)
    title = str(rng.choice(role["titles"])) if rng.random() < 0.85 else ""
    keywords = _sample(rng, list(role["keywords"]), 3)

    # Một số kỹ năng thật không được ghi trong CV -> mô hình phải chịu nhiễu trích xuất như thực tế.
    listed = [s for s in true_skills if rng.random() < 0.85]
    lines = [title or "Ứng viên", f"Mục tiêu nghề nghiệp: phát triển trong lĩnh vực {keywords[0]} và {keywords[1]}."]
    lines += ["Kỹ năng", ", ".join(_mention(rng, s) for s in listed) or "Tin học văn phòng"]
    lines.append("Kinh nghiệm làm việc")
    if years == 0:
        lines.append("Chưa có kinh nghiệm chính thức, đã tham gia các dự án học tập.")
    elif rng.random() < 0.55:
        lines.append(f"{years:g} năm kinh nghiệm ở vị trí {title or 'liên quan'}, phụ trách {keywords[2]}.")
    else:
        end_offset = int(rng.integers(0, 4))
        start_year, start_month = _months_ago(today, end_offset + int(years * 12))
        end = "nay" if end_offset == 0 else "{1:02d}/{0}".format(*_months_ago(today, end_offset))
        lines.append(f"{start_month:02d}/{start_year} - {end}: {title or 'Nhân viên'} tại Công ty Demo, phụ trách {keywords[2]}.")
    lines += ["Học vấn", f"{EDUCATION_TEXT[education]}."]
    text = "\n".join(lines)

    extractor = get_extractor()
    candidate = CandidateDoc(
        text=text,
        title=title,
        skills=extractor.extract(text),
        experience_years=parse_experience_years(text, today=today) or 0.0,
        education_level=parse_education_level(text),
        location=location,
        desired_salary=desired_salary,
    )
    truth = {
        "skills": extractor.expand({extractor.key(s) for s in true_skills}),
        "relevance": relevance,
        "years": years,
        "education": education,
    }
    return candidate, truth


def _recruiter_decision(rng, truth, job, level, job_education):
    required, preferred = job.required_skills, job.preferred_skills
    required_coverage = len(truth["skills"] & required) / len(required)
    preferred_coverage = len(truth["skills"] & preferred) / len(preferred) if preferred else 1.0
    gap = truth["years"] - job.min_years
    experience = 1.0 if gap >= 0 else max(0.0, 1 + gap / 3)
    overqualified = 1.0 if gap > 6 and level in ("ENTRY", "JUNIOR") else 0.0
    education_ok = 1.0 if truth["education"] >= job_education else 0.0
    candidate_location = truth["location"]
    location = 1.0 if job.work_mode == "REMOTE" or candidate_location == job.location else (0.5 if job.work_mode == "HYBRID" else 0.0)
    salary = 1.0 if truth["desired_salary"] <= job.salary_max else max(0.0, 1 - (truth["desired_salary"] - job.salary_max) / job.salary_max)
    utility = (
        -6.2 + 3.2 * required_coverage + 1.0 * preferred_coverage + 1.6 * truth["relevance"] + 1.5 * experience
        + 0.5 * education_ok + 0.6 * location + 0.8 * salary - 0.7 * overqualified
    )
    if required_coverage < 0.5:
        utility -= 1.5  # loại sớm khi thiếu phần lớn kỹ năng bắt buộc
    probability = 1 / (1 + np.exp(-1.4 * utility))
    return int(rng.random() < probability)


def generate_training_data(samples=4000, seed=42, today=None):
    """Trả về (candidates, jobs, labels) với nhãn 1 = được mời phỏng vấn/nhận việc."""
    rng = np.random.default_rng(seed)
    today = today or date.today()
    candidates, jobs, labels = [], [], []
    for _ in range(samples):
        role_name, level, job_education, job = _make_job(rng, today)
        candidate, truth = _make_candidate(rng, role_name, job, today)
        truth["location"] = candidate.location
        truth["desired_salary"] = candidate.desired_salary
        labels.append(_recruiter_decision(rng, truth, job, level, job_education))
        candidates.append(candidate)
        jobs.append(job)
    return candidates, jobs, labels
