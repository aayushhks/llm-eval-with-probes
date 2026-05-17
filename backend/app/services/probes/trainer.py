"""Train logistic-regression probes on hidden state activations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score

from app.core.logging import get_logger
from app.services.probes.extractor import PROBE_LAYER, extract_activations
from app.services.probes.scorer import PROBES_DIR
from app.services.probes.training_data import ALL_PROBES

logger = get_logger("probes.trainer")


@dataclass
class TrainedProbe:
    name: str
    classifier: LogisticRegression
    n_train: int
    n_pos: int
    accuracy_cv: float
    classification_report: dict[str, Any]


def _featurize_dataset(examples: list[tuple[str, str, int]]) -> tuple[np.ndarray, np.ndarray]:
    """Run the extractor on every (diff, review) pair."""
    X = []
    y = []
    for i, (diff, review, label) in enumerate(examples):
        logger.info("extracting", i=i + 1, total=len(examples))
        X.append(extract_activations(diff, review))
        y.append(label)
    return np.vstack(X), np.array(y)


def train_probe(name: str, examples: list[tuple[str, str, int]]) -> TrainedProbe:
    """Featurize, cross-validate, fit a logistic regression probe."""
    if len({lbl for _, _, lbl in examples}) < 2:
        raise ValueError(f"Probe {name}: need both label 0 and 1 in training data")

    X, y = _featurize_dataset(examples)
    logger.info("featurized", probe=name, X_shape=X.shape, n_pos=int(y.sum()))

    clf = LogisticRegression(max_iter=2000, C=1.0)

    # Stratified k-fold CV honest accuracy estimate
    n_splits = min(5, int(min(y.sum(), len(y) - y.sum())))  # cap by smaller class
    if n_splits >= 2:
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        cv_scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")
        acc_cv = float(cv_scores.mean())
        logger.info("cv_accuracy", probe=name, mean=acc_cv, std=float(cv_scores.std()))
    else:
        acc_cv = float("nan")
        logger.warning("not_enough_data_for_cv", probe=name, n=len(y))

    # Final fit on all data
    clf.fit(X, y)
    train_acc = accuracy_score(y, clf.predict(X))
    report = classification_report(y, clf.predict(X), output_dict=True)

    logger.info("trained", probe=name, train_accuracy=train_acc)
    return TrainedProbe(
        name=name,
        classifier=clf,
        n_train=len(y),
        n_pos=int(y.sum()),
        accuracy_cv=acc_cv,
        classification_report=report,
    )


def save_probe(probe: TrainedProbe) -> Path:
    PROBES_DIR.mkdir(parents=True, exist_ok=True)
    path = PROBES_DIR / f"{probe.name}.joblib"
    joblib.dump(probe.classifier, path)

    meta_path = PROBES_DIR / f"{probe.name}.meta.json"
    with meta_path.open("w") as f:
        json.dump(
            {
                "name": probe.name,
                "n_train": probe.n_train,
                "n_pos": probe.n_pos,
                "accuracy_cv": probe.accuracy_cv,
                "classification_report": probe.classification_report,
                "extractor_layer": PROBE_LAYER,
            },
            f,
            indent=2,
        )
    return path


def train_all() -> None:
    """Train every probe and save under backend/probes/."""
    for name, examples in ALL_PROBES.items():
        probe = train_probe(name, examples)
        path = save_probe(probe)
        print(
            f"  ✓ {name}: n={probe.n_train} pos={probe.n_pos} "
            f"acc_cv={probe.accuracy_cv:.3f} -> {path}"
        )
