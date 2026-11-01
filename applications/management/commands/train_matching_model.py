import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from applications.ai.model import train_matching_model
from applications.ai.synthetic import generate_training_data
from applications.matching import candidate_document, job_document, skill_extractor
from applications.models import Application
from candidates.models import Resume
from jobs.models import Job

POSITIVE_STATUSES = (Application.Status.INTERVIEW, Application.Status.ACCEPTED)
NEGATIVE_STATUSES = (Application.Status.REJECTED,)


class Command(BaseCommand):
    help = "Huan luyen mo hinh ML tinh diem tuong thich giua CV ung vien va mo ta cong viec."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=["synthetic", "database", "combined"],
            default="synthetic",
            help="synthetic: du lieu mo phong (cold-start); database: ket qua tuyen dung that "
            "(INTERVIEW/ACCEPTED = phu hop, REJECTED = khong phu hop); combined: ca hai.",
        )
        parser.add_argument("--samples", type=int, default=4000, help="So cap CV - JD mo phong.")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--min-labels", type=int, default=30, help="So ho so toi thieu cho moi nhan khi dung database.")
        parser.add_argument("--output", default=None, help="Duong dan file mo hinh (mac dinh MATCHING_MODEL_PATH).")

    def handle(self, *args, **options):
        source = options["source"]
        candidates, jobs, labels = [], [], []
        if source in ("synthetic", "combined"):
            synthetic = generate_training_data(options["samples"], seed=options["seed"])
            for target, values in zip((candidates, jobs, labels), synthetic):
                target.extend(values)
        if source in ("database", "combined"):
            database = self.database_samples()
            positives, negatives = database[2].count(1), database[2].count(0)
            if min(positives, negatives) < options["min_labels"]:
                raise CommandError(
                    f"Database co {positives} ho so INTERVIEW/ACCEPTED va {negatives} ho so REJECTED; "
                    f"can toi thieu {options['min_labels']} ho so moi nhan."
                )
            for target, values in zip((candidates, jobs, labels), database):
                target.extend(values)

        self.stdout.write(f"Training on {len(labels)} samples (source={source}, positive={sum(labels)})...")
        try:
            model = train_matching_model(
                candidates, jobs, labels, extra_corpus=self.database_corpus(), seed=options["seed"], data_source=source
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        path = model.save(Path(options["output"] or settings.MATCHING_MODEL_PATH))
        report_path = path.with_suffix(".json")
        report_path.write_text(json.dumps(model.metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        metadata = model.metadata
        self.stdout.write("Cross-validation ROC-AUC: " + ", ".join(f"{k}={v}" for k, v in metadata["cv_roc_auc"].items()))
        self.stdout.write(f"Selected model: {metadata['model_name']}")
        self.stdout.write("Hold-out metrics: " + ", ".join(f"{k}={v}" for k, v in metadata["test_metrics"].items()))
        if source == "synthetic":
            self.stdout.write(self.style.WARNING("Metrics are measured on simulated labels, not on real hiring outcomes."))
        self.stdout.write(self.style.SUCCESS(f"Model saved to {path} (report: {report_path.name})"))

    def database_samples(self):
        extractor = skill_extractor()
        applications = Application.objects.filter(status__in=[*POSITIVE_STATUSES, *NEGATIVE_STATUSES]).select_related(
            "candidate", "job", "resume"
        )
        candidates, jobs, labels = [], [], []
        for application in applications:
            candidates.append(candidate_document(application.candidate, application.resume, extractor))
            jobs.append(job_document(application.job, extractor))
            labels.append(int(application.status in POSITIVE_STATUSES))
        return candidates, jobs, labels

    def database_corpus(self):
        """Văn bản JD/CV hiện có giúp bộ TF-IDF học từ vựng thực tế (không dùng nhãn)."""
        texts = [
            "\n".join(filter(None, [job.title, job.description, job.requirements, job.responsibilities]))
            for job in Job.objects.only("title", "description", "requirements", "responsibilities")
        ]
        texts += list(Resume.objects.exclude(resume_text="").values_list("resume_text", flat=True))
        return texts
