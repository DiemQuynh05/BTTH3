from django.core.management.base import BaseCommand

from applications.matching import load_matching_model, rescore_applications
from applications.models import Application
from candidates.models import Resume
from candidates.services import process_resume


class Command(BaseCommand):
    help = "Phan tich lai CV va tinh lai diem tuong thich cho cac ho so ung tuyen."

    def add_arguments(self, parser):
        parser.add_argument("--job", type=int, help="Chi tinh lai cho mot tin tuyen dung.")
        parser.add_argument("--skip-resumes", action="store_true", help="Khong phan tich lai CV truoc khi cham diem.")

    def handle(self, *args, **options):
        applications = Application.objects.all()
        resumes = Resume.objects.all()
        if options["job"]:
            applications = applications.filter(job_id=options["job"])
            resumes = resumes.filter(candidate__applications__job_id=options["job"]).distinct()
        if not options["skip_resumes"]:
            parsed = sum(1 for resume in resumes if process_resume(resume))
            self.stdout.write(f"Parsed {parsed} resumes.")
        model = load_matching_model()
        method = f"ML model ({model.metadata['model_name']})" if model else "rule-based fallback (run train_matching_model first)"
        count = rescore_applications(applications)
        self.stdout.write(self.style.SUCCESS(f"Rescored {count} applications using {method}."))
