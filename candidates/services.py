import logging

from applications.ai.cv_parser import extract_text, parse_resume_text
from applications.matching import skill_extractor

logger = logging.getLogger(__name__)


def process_resume(resume):
    """Trích xuất văn bản CV, nhận diện kỹ năng/kinh nghiệm/học vấn và lưu kết quả vào Resume."""
    extracted = ""
    if resume.file:
        try:
            with resume.file.open("rb") as handle:
                extracted = extract_text(handle, resume.original_filename or resume.file.name)
        except OSError:
            logger.warning("Cannot open resume file %s", resume.file.name)
    if extracted:
        resume.resume_text = extracted
    extractor = skill_extractor()
    parsed = parse_resume_text(resume.resume_text, extractor=extractor)
    resume.parsed_data = {**parsed.to_dict(extractor), "extracted_from_file": bool(extracted)}
    resume.save(update_fields=["resume_text", "parsed_data"])
    return resume
