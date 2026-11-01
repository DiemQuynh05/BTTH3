import re
import unicodedata

_DASHES = str.maketrans({"–": "-", "—": "-", "−": "-"})
_DISALLOWED = re.compile(r"[^a-z0-9+#./\-\s]")
_SPACES = re.compile(r"\s+")

TOKEN_PATTERN = r"[a-z0-9][a-z0-9+#]+"
STOP_WORDS = [
    "va", "cac", "cua", "trong", "voi", "cho", "la", "co", "duoc", "nhung", "mot", "nay", "de", "tai",
    "khi", "tu", "den", "theo", "ve", "se", "da", "dang", "hoac", "cung", "nhu", "thi", "ra", "vao",
    "and", "or", "the", "of", "to", "in", "for", "with", "on", "at", "is", "are", "be", "an",
]


def strip_accents(text):
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def normalize_text(text):
    """Chuẩn hóa tiếng Việt: bỏ dấu, chữ thường, giữ ký tự dùng trong tên kỹ năng (c#, c++, .net)."""
    if not text:
        return ""
    text = strip_accents(str(text)).lower().translate(_DASHES)
    text = _DISALLOWED.sub(" ", text)
    return _SPACES.sub(" ", text).strip()
