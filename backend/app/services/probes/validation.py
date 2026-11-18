"""Leakage-aware evaluation of cached probe features; never fits on a held-out diff."""

from __future__ import annotations

import hashlib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    brier_score_loss,
)
from sklearn.model_selection import LeaveOneGroupOut


def diff_group(diff: str) -> str:
    # Whitespace normalization catches exact formatting variants, not semantic duplicates.
    return hashlib.sha256(" ".join(diff.split()).encode()).hexdigest()


def validate_features(X: np.ndarray, y: np.ndarray, groups: list[str]) -> dict:
    X, y = np.asarray(X), np.asarray(y)
    if X.ndim != 2 or len(X) != len(y) or len(y) != len(groups):
        raise ValueError("Features, labels and diff groups must have matching lengths")
    if not np.isfinite(X).all() or set(np.unique(y)) != {0, 1}:
        raise ValueError("Finite features and both binary labels are required")
    if len(set(groups)) < 2:
        return {
            "status": "insufficient_groups",
            "n_examples": len(y),
            "n_groups": len(set(groups)),
            "coverage": 0,
            "metrics": None,
            "folds": [],
        }
    scores = np.full(len(y), np.nan)
    folds = []
    for train, test in LeaveOneGroupOut().split(X, y, groups):
        record = {
            "held_out_group": groups[int(test[0])],
            "n_train": len(train),
            "n_test": len(test),
            "train_groups": sorted(set(groups[i] for i in train)),
        }
        if len(np.unique(y[train])) != 2:
            record["status"] = "skipped_single_class_training"
        else:
            model = LogisticRegression(max_iter=2000, C=1.0, random_state=42)
            model.fit(X[train], y[train])
            scores[test] = model.predict_proba(X[test])[:, 1]
            record["status"] = "evaluated"
        folds.append(record)
    full = bool(np.isfinite(scores).all())
    metrics = None
    if full:
        pred = scores >= 0.5  # Fixed in advance; no tuning on held-out labels.
        metrics = {
            "accuracy": float(accuracy_score(y, pred)),
            "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
            "precision": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0)),
            "f1": float(f1_score(y, pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y, scores)),
            "brier_score": float(brier_score_loss(y, scores)),
            "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
        }
    return {
        "status": "complete" if full else "incomplete_group_coverage",
        "protocol": "leave-one-code-diff-out",
        "threshold": 0.5,
        "threshold_selection": "fixed before evaluation; not optimized",
        "n_examples": len(y),
        "n_groups": len(set(groups)),
        "coverage": float(np.isfinite(scores).mean()),
        "metrics": metrics,
        "folds": folds,
        "out_of_fold_scores": [float(p) if np.isfinite(p) else None for p in scores],
    }
