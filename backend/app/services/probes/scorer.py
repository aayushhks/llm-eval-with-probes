"""Apply trained probes to (diff, review) pairs."""

from __future__ import annotations

import functools
from dataclasses import dataclass

# Lazy import below; importing extractor at module-load triggers MLX
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression

from app.core.logging import get_logger
from app.services.probes.training_data import ALL_PROBES

PROBES_DIR = Path(__file__).resolve().parents[3] / "probes"

logger = get_logger("probes.scorer")


@dataclass
class ProbeScores:
    """Per-case probe outputs."""

    is_sycophantic: float | None  # 0..1 probability
    is_refusing: float | None
    is_ungrounded: float | None
    is_uncertain: float | None

    def to_dict(self) -> dict[str, float | None]:
        return {
            "is_sycophantic": self.is_sycophantic,
            "is_refusing": self.is_refusing,
            "is_ungrounded": self.is_ungrounded,
            "is_uncertain": self.is_uncertain,
        }


@functools.cache
def _load_probes() -> dict[str, LogisticRegression]:
    loaded: dict[str, LogisticRegression] = {}
    for name in ALL_PROBES:
        path = PROBES_DIR / f"{name}.joblib"
        if not path.exists():
            logger.warning("probe_missing", probe=name, path=str(path))
            continue
        loaded[name] = joblib.load(path)
    return loaded


def probes_available() -> bool:
    """True iff all 4 probes have been trained and saved."""
    return all((PROBES_DIR / f"{name}.joblib").exists() for name in ALL_PROBES)


def score_with_probes(diff: str, model_review: str) -> ProbeScores:
    """Run all trained probes and return per-behavior probabilities."""
    from app.services.probes.extractor import extract_activations  # lazy

    probes = _load_probes()
    if not probes:
        return ProbeScores(None, None, None, None)

    activations = extract_activations(diff, model_review).reshape(1, -1)

    results: dict[str, float | None] = dict.fromkeys(ALL_PROBES, None)
    for name, clf in probes.items():
        # predict_proba returns [[p_0, p_1]]; take p_1
        prob = float(clf.predict_proba(activations)[0, 1])
        results[name] = prob

    return ProbeScores(
        is_sycophantic=results["is_sycophantic"],
        is_refusing=results["is_refusing"],
        is_ungrounded=results["is_ungrounded"],
        is_uncertain=results["is_uncertain"],
    )
