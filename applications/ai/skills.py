import re
from functools import lru_cache

from .text import normalize_text

# Tên chuẩn -> các biến thể thường gặp trong CV/JD (viết dưới dạng đã chuẩn hóa, không dấu).
SKILL_TAXONOMY = {
    "SQL": ("sql", "t-sql", "pl/sql", "truy van du lieu"),
    "MySQL": ("mysql",),
    "PostgreSQL": ("postgresql", "postgres"),
    "MongoDB": ("mongodb",),
    "Excel": ("excel", "ms excel", "microsoft excel", "google sheets", "pivot table"),
    "Python": ("python",),
    "Pandas": ("pandas",),
    "Power BI": ("power bi", "powerbi", "dax"),
    "Tableau": ("tableau",),
    "Thống kê": ("thong ke", "statistics", "xac suat thong ke"),
    "Machine Learning": ("machine learning", "hoc may", "ml", "scikit-learn", "sklearn"),
    "Deep Learning": ("deep learning", "hoc sau", "tensorflow", "pytorch", "keras"),
    "Spark": ("spark", "pyspark", "apache spark"),
    "Airflow": ("airflow", "apache airflow"),
    "ETL": ("etl", "elt", "data pipeline"),
    "HTML": ("html", "html5"),
    "CSS": ("css", "css3", "scss", "sass", "tailwind", "bootstrap"),
    "JavaScript": ("javascript", "js", "es6"),
    "TypeScript": ("typescript",),
    "React": ("react", "reactjs", "react.js"),
    "Node.js": ("node.js", "nodejs", "node js", "expressjs"),
    "Django": ("django",),
    "REST API": ("rest api", "restful", "restful api"),
    "Java": ("java",),
    "Spring Boot": ("spring boot", "springboot", "spring framework"),
    "C#": ("c#", ".net", "asp.net", "dotnet"),
    "Docker": ("docker", "docker compose"),
    "AWS": ("aws", "amazon web services"),
    "Linux": ("linux", "ubuntu", "centos", "bash"),
    "Git": ("git", "github", "gitlab", "bitbucket"),
    "Jira": ("jira", "confluence"),
    "Agile": ("agile", "scrum", "kanban"),
    "Kiểm thử phần mềm": ("kiem thu", "kiem thu phan mem", "software testing", "testing", "tester", "qa", "qc", "test case"),
    "Selenium": ("selenium", "automation test", "kiem thu tu dong"),
    "Figma": ("figma",),
    "UI/UX": ("ui/ux", "ux/ui", "ui ux", "ux", "user experience", "thiet ke giao dien"),
    "Photoshop": ("photoshop", "adobe photoshop", "illustrator"),
    "Phân tích nghiệp vụ": ("phan tich nghiep vu", "business analysis", "brd", "srs", "phan tich yeu cau", "requirement analysis"),
    "UML": ("uml", "bpmn", "use case"),
    "Giao tiếp": ("giao tiep", "communication", "thuyet trinh", "presentation"),
    "Tư duy logic": ("tu duy logic", "logical thinking", "problem solving", "giai quyet van de"),
    "Tiếng Anh": ("tieng anh", "english", "ielts", "toeic", "toefl"),
    "Hỗ trợ CNTT": ("ho tro cntt", "ho tro ky thuat", "it support", "helpdesk", "help desk", "technical support"),
    "Mạng máy tính": ("mang may tinh", "networking", "ccna", "tcp/ip"),
    "Windows Server": ("windows server", "active directory"),
    "Marketing số": ("marketing so", "digital marketing", "online marketing"),
    "SEO": ("seo", "toi uu cong cu tim kiem"),
    "Google Ads": ("google ads", "adwords", "facebook ads"),
    "Content Marketing": ("content marketing", "copywriting", "content writing", "sang tao noi dung"),
}

# Biết kỹ năng bên trái nghĩa là biết kỹ năng bên phải (chỉ áp dụng cho phía ứng viên).
SKILL_IMPLIES = {
    "Pandas": ("Python",),
    "Django": ("Python",),
    "React": ("JavaScript",),
    "TypeScript": ("JavaScript",),
    "Node.js": ("JavaScript",),
    "Spring Boot": ("Java",),
    "MySQL": ("SQL",),
    "PostgreSQL": ("SQL",),
    "Selenium": ("Kiểm thử phần mềm",),
}


class SkillExtractor:
    """Nhận diện kỹ năng chuẩn hóa từ văn bản bằng từ điển kỹ năng + biến thể."""

    def __init__(self, extra_skills=()):
        self.display = {}
        alias_to_key = {}
        for canonical, aliases in SKILL_TAXONOMY.items():
            key = normalize_text(canonical)
            self.display[key] = canonical
            for alias in (canonical, *aliases):
                alias_to_key[normalize_text(alias)] = key
        for name in extra_skills:
            norm = normalize_text(name)
            if not norm:
                continue
            key = alias_to_key.setdefault(norm, norm)
            self.display.setdefault(key, name)
        self.alias_to_key = alias_to_key
        self.implies = {
            normalize_text(source): {normalize_text(target) for target in targets}
            for source, targets in SKILL_IMPLIES.items()
        }
        alternation = "|".join(re.escape(alias) for alias in sorted(alias_to_key, key=len, reverse=True))
        self._pattern = re.compile(rf"(?<![a-z0-9+#])(?:{alternation})(?![a-z0-9+#])")

    def key(self, name):
        norm = normalize_text(name)
        return self.alias_to_key.get(norm, norm)

    def extract(self, text, expand=True):
        found = {self.alias_to_key[match.group(0)] for match in self._pattern.finditer(normalize_text(text))}
        return self.expand(found) if expand else found

    def expand(self, keys):
        expanded = set(keys)
        for key in keys:
            expanded |= self.implies.get(key, set())
        return expanded

    def names(self, keys):
        return sorted(self.display.get(key, key) for key in keys)


@lru_cache(maxsize=32)
def get_extractor(extra_skills=()):
    return SkillExtractor(tuple(extra_skills))
