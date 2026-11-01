from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURE_LABELS, FEATURE_NAMES, feature_matrix
from .skills import get_extractor
from .text import STOP_WORDS, TOKEN_PATTERN, normalize_text

ARTIFACT_VERSION = 1
TOP_FACTORS = 4


@dataclass
class MatchResult:
    score: float
    explanation: dict


def build_vectorizer():
    return TfidfVectorizer(
        preprocessor=normalize_text,
        token_pattern=TOKEN_PATTERN,
        stop_words=STOP_WORDS,
        ngram_range=(1, 2),
        sublinear_tf=True,
        max_features=30_000,
    )


def candidate_classifiers(seed):
    return {
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000)),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_depth=3, learning_rate=0.06, max_iter=250, l2_regularization=1.0, random_state=seed
        ),
    }


def train_matching_model(candidates, jobs, labels, extra_corpus=(), seed=42, data_source="synthetic"):
    """Vector hóa văn bản, chọn mô hình tốt nhất theo ROC-AUC (cross-validation) và đánh giá trên tập kiểm thử."""
    y = np.asarray(labels, dtype=int)
    class_counts = np.bincount(y, minlength=2)
    if class_counts.min() < 4:
        raise ValueError("Cần ít nhất 4 mẫu cho mỗi nhãn (phù hợp / không phù hợp) để huấn luyện.")
    corpus = [c.text for c in candidates] + [j.text for j in jobs] + [c.title for c in candidates] + [j.title for j in jobs]
    vectorizer = build_vectorizer().fit([text for text in [*corpus, *extra_corpus] if text])
    X = feature_matrix(candidates, jobs, vectorizer)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=seed)
    folds = int(min(5, np.bincount(y_train).min()))
    cv = StratifiedKFold(n_splits=max(2, folds), shuffle=True, random_state=seed)
    cv_auc = {
        name: float(cross_val_score(classifier, X_train, y_train, cv=cv, scoring="roc_auc").mean())
        for name, classifier in candidate_classifiers(seed).items()
    }
    best_name = max(cv_auc, key=cv_auc.get)
    evaluated = candidate_classifiers(seed)[best_name].fit(X_train, y_train)
    probabilities = evaluated.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    metrics = {
        "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4),
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "precision": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, predictions, zero_division=0)), 4),
        "brier": round(float(brier_score_loss(y_test, probabilities)), 4),
    }
    # Sau khi đánh giá, huấn luyện lại trên toàn bộ dữ liệu để triển khai.
    classifier = candidate_classifiers(seed)[best_name].fit(X, y)
    metadata = {
        "model_name": best_name,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": data_source,
        "samples": int(len(y)),
        "positive_rate": round(float(y.mean()), 4),
        "test_samples": int(len(y_test)),
        "cv_roc_auc": {name: round(value, 4) for name, value in cv_auc.items()},
        "test_metrics": metrics,
        "sklearn_version": sklearn.__version__,
        "feature_names": list(FEATURE_NAMES),
    }
    return MatchingModel(vectorizer, classifier, X.mean(axis=0), metadata)


class MatchingModel:
    def __init__(self, vectorizer, classifier, baseline, metadata):
        self.vectorizer = vectorizer
        self.classifier = classifier
        self.baseline = np.asarray(baseline, dtype=float)
        self.metadata = metadata

    def predict_proba(self, candidates, jobs):
        return self.classifier.predict_proba(feature_matrix(candidates, jobs, self.vectorizer))[:, 1]

    def score(self, candidate, job, extractor=None):
        extractor = extractor or get_extractor()
        features = feature_matrix([candidate], [job], self.vectorizer)[0]
        # Giải thích kiểu occlusion: thay từng đặc trưng bằng giá trị trung bình lúc huấn luyện
        # và đo mức thay đổi xác suất -> tác động (điểm) của đặc trưng đó với cặp CV - JD này.
        variants = np.tile(features, (len(FEATURE_NAMES) + 1, 1))
        for index in range(len(FEATURE_NAMES)):
            variants[index + 1, index] = self.baseline[index]
        probabilities = self.classifier.predict_proba(variants)[:, 1]
        probability = float(probabilities[0])
        impacts = (probability - probabilities[1:]) * 100
        order = np.argsort(-np.abs(impacts))[:TOP_FACTORS]
        required, preferred = job.required_skills, job.preferred_skills
        explanation = {
            "method": "ml",
            "model": self.metadata["model_name"],
            "trained_at": self.metadata["trained_at"],
            "data_source": self.metadata["data_source"],
            "probability": round(probability, 4),
            "required_skills": f"{len(candidate.skills & required)}/{len(required)}",
            "preferred_skills": f"{len(candidate.skills & preferred)}/{len(preferred)}",
            "matched_skills": extractor.names(candidate.skills & (required | preferred)),
            "missing_required_skills": extractor.names(required - candidate.skills),
            "missing_preferred_skills": extractor.names(preferred - candidate.skills),
            "features": {name: round(float(value), 4) for name, value in zip(FEATURE_NAMES, features)},
            "top_factors": [
                {"feature": FEATURE_NAMES[i], "label": FEATURE_LABELS[FEATURE_NAMES[i]], "impact": round(float(impacts[i]), 2)}
                for i in order
            ],
        }
        return MatchResult(score=round(probability * 100, 2), explanation=explanation)

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "version": ARTIFACT_VERSION,
                "vectorizer": self.vectorizer,
                "classifier": self.classifier,
                "baseline": self.baseline,
                "metadata": self.metadata,
            },
            path,
        )
        return path

    @classmethod
    def load(cls, path):
        artifact = joblib.load(path)
        if artifact.get("version") != ARTIFACT_VERSION or artifact["metadata"].get("feature_names") != list(FEATURE_NAMES):
            raise ValueError("File mô hình không tương thích với phiên bản code hiện tại, hãy huấn luyện lại.")
        return cls(artifact["vectorizer"], artifact["classifier"], artifact["baseline"], artifact["metadata"])
