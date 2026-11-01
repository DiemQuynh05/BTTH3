import io
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .skills import get_extractor
from .text import normalize_text

logger = logging.getLogger(__name__)
# pypdf ghi cảnh báo cho từng lỗi cấu trúc nhỏ của PDF; chỉ giữ lỗi nghiêm trọng.
logging.getLogger("pypdf").setLevel(logging.ERROR)

MAX_PDF_PAGES = 20
MAX_TEXT_LENGTH = 50_000

EDUCATION_LABELS = {
    0: "Không xác định",
    1: "Trung học/Trung cấp",
    2: "Cao đẳng",
    3: "Đại học",
    4: "Thạc sĩ",
    5: "Tiến sĩ",
}
_EDUCATION_PATTERNS = (
    (5, re.compile(r"\b(tien si|phd|ph\.d|doctor of)\b")),
    (4, re.compile(r"\b(thac si|cao hoc|mba|(?<!scrum )master)\b")),
    (3, re.compile(r"\b(dai hoc|cu nhan|ky su|bachelor|university)\b")),
    (2, re.compile(r"\b(cao dang|college)\b")),
    (1, re.compile(r"\b(trung cap|thpt|trung hoc|high school)\b")),
)

_NUMBER = r"(?<![\d.])(\d{1,2}(?:[.,]\d)?)"
_YEAR_UNIT = r"\s*\+?\s*(?:nam|years?|yrs?)"
_EXPLICIT_YEARS = (
    re.compile(_NUMBER + _YEAR_UNIT + r"\s*(?:kinh nghiem|of experience|experience|lam viec)"),
    re.compile(r"(?:kinh nghiem|experience)(?: lam viec)?\s*(?:hon |tren |over |more than )?" + _NUMBER + _YEAR_UNIT),
)
_EXPLICIT_MONTHS = re.compile(_NUMBER + r"\s*\+?\s*(?:thang|months?)\s*(?:kinh nghiem|of experience|experience|lam viec)")
_DATE_RANGE = re.compile(
    r"(?:(\d{1,2})[/.-])?((?:19|20)\d{2})\s*(?:-|den|to)\s*"
    r"(?:(?:(\d{1,2})[/.-])?((?:19|20)\d{2})|(nay|hien tai|hien nay|present|now|current))"
)
_EXPERIENCE_HEADINGS = ("kinh nghiem lam viec", "kinh nghiem", "work experience", "experience", "qua trinh cong tac", "employment history")
_OTHER_HEADINGS = (
    "hoc van", "trinh do hoc van", "education", "ky nang", "skills", "du an", "projects", "chung chi", "certifications",
    "hoat dong", "activities", "so thich", "interests", "muc tieu", "objective", "thong tin ca nhan", "giai thuong",
    "awards", "nguoi tham chieu", "references",
)


@dataclass
class ParsedResume:
    skills: set = field(default_factory=set)
    experience_years: float | None = None
    education_level: int = 0
    word_count: int = 0

    def to_dict(self, extractor=None):
        extractor = extractor or get_extractor()
        return {
            "skills": extractor.names(self.skills),
            "experience_years": self.experience_years,
            "education_level": self.education_level,
            "education_label": EDUCATION_LABELS[self.education_level],
            "word_count": self.word_count,
        }


def extract_text(data, filename):
    """Trích xuất văn bản từ CV (PDF, DOCX, TXT). Lỗi định dạng trả về chuỗi rỗng."""
    if hasattr(data, "read"):
        data = data.read()
    extension = Path(filename or "").suffix.lower()
    try:
        if extension == ".pdf":
            text = _pdf_text(data)
        elif extension == ".docx":
            text = _docx_text(data)
        elif extension == ".txt":
            text = data.decode("utf-8", errors="ignore")
        else:
            return ""
    except Exception as exc:  # file hỏng hoặc thư viện chưa cài: CV vẫn được lưu, chỉ không có text
        logger.warning("Cannot extract text from resume %s: %s", filename, exc)
        return ""
    return text[:MAX_TEXT_LENGTH].strip()


def _pdf_text(data):
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages[:MAX_PDF_PAGES])


def _docx_text(data):
    from docx import Document

    document = Document(io.BytesIO(data))
    lines = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(lines)


def parse_education_level(text, mode="max"):
    """Bậc học cao nhất (CV) hoặc thấp nhất được chấp nhận (JD, mode='min')."""
    normalized = normalize_text(text)
    levels = [level for level, pattern in _EDUCATION_PATTERNS if pattern.search(normalized)]
    if not levels:
        return 0
    return max(levels) if mode == "max" else min(levels)


def parse_experience_years(text, today=None):
    """Số năm kinh nghiệm: ưu tiên câu nêu rõ, sau đó cộng các mốc thời gian trong mục Kinh nghiệm."""
    normalized = normalize_text(text)
    explicit = [float(value.replace(",", ".")) for pattern in _EXPLICIT_YEARS for value in pattern.findall(normalized)]
    explicit += [float(value.replace(",", ".")) / 12 for value in _EXPLICIT_MONTHS.findall(normalized)]
    explicit = [value for value in explicit if value <= 40]
    if explicit:
        return round(max(explicit), 1)
    months = _experience_section_months(text, today or date.today())
    return round(months / 12, 1) if months else None


def _experience_section_months(text, today):
    intervals = []
    in_section = False
    for raw_line in (text or "").splitlines():
        line = normalize_text(raw_line)
        if not line:
            continue
        if len(line.split()) <= 5:
            if any(line.startswith(heading) for heading in _EXPERIENCE_HEADINGS):
                in_section = True
                continue
            if any(line.startswith(heading) for heading in _OTHER_HEADINGS):
                in_section = False
                continue
        if not in_section:
            continue
        for start_month, start_year, end_month, end_year, ongoing in _DATE_RANGE.findall(line):
            start = int(start_year) * 12 + (int(start_month) - 1 if start_month else 0)
            if ongoing:
                end = today.year * 12 + today.month - 1
            else:
                end = int(end_year) * 12 + (int(end_month) - 1 if end_month else 0)
            if end > start:
                intervals.append((start, end))
    total, covered_until = 0, None
    for start, end in sorted(intervals):
        if covered_until is not None:
            start = max(start, covered_until)
        if end > start:
            total += end - start
        covered_until = end if covered_until is None else max(covered_until, end)
    return total


def parse_resume_text(text, extractor=None, today=None):
    extractor = extractor or get_extractor()
    return ParsedResume(
        skills=extractor.extract(text),
        experience_years=parse_experience_years(text, today=today),
        education_level=parse_education_level(text),
        word_count=len(normalize_text(text).split()),
    )
