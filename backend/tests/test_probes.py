"""Tests for probe training and scoring. We mock the MLX extractor so tests
run fast and without downloading weights."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from app.services.probes.scorer import (
    ProbeScores,
    probes_available,
    score_with_probes,
)
from app.services.probes.trainer import save_probe, train_probe


def _mock_extract(diff: str, model_review: str, **kwargs) -> np.ndarray:
    """Deterministic fake activations: hash → 32-dim vector."""
    seed = abs(hash(diff + model_review)) % (2**32)
    rng = np.random.default_rng(seed)
    # Inject a signal: presence of "looks good" boosts a specific dimension
    vec = rng.normal(size=32).astype(np.float32)
    if "looks good" in model_review.lower() or "approved" in model_review.lower():
        vec[0] += 5.0
    return vec


@pytest.fixture
def fake_examples() -> list[tuple[str, str, int]]:
    """13 examples per side, split label 1 if 'looks good'/'approved' in review."""
    pos = [
        ("diff", "Looks good! Clean refactor.", 1),
        ("diff", "Approved. Nice work.", 1),
        ("diff", "LGTM looks good", 1),
        ("diff", "Looks good to me.", 1),
        ("diff", "Approved.", 1),
        ("diff", "looks GOOD!", 1),
    ]
    neg = [
        ("diff", "This has a critical security flaw.", 0),
        ("diff", "Blocked: hardcoded secrets.", 0),
        ("diff", "Reject. Do not merge.", 0),
        ("diff", "The function never validates anything.", 0),
        ("diff", "Bug: pagination off-by-one.", 0),
        ("diff", "Wrong: integer division loses precision.", 0),
    ]
    return pos + neg


def test_train_probe_runs_end_to_end(fake_examples) -> None:
    with patch("app.services.probes.trainer.extract_activations", side_effect=_mock_extract):
        probe = train_probe("test_probe", fake_examples)
    assert probe.n_train == 12
    assert probe.n_pos == 6
    # The injected signal makes this fully separable
    assert probe.accuracy_cv > 0.7


def test_save_and_load_probe(fake_examples, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.probes.trainer.PROBES_DIR", tmp_path)
    monkeypatch.setattr("app.services.probes.scorer.PROBES_DIR", tmp_path)

    with patch("app.services.probes.trainer.extract_activations", side_effect=_mock_extract):
        probe = train_probe("is_sycophantic", fake_examples)
        save_probe(probe)

    assert (tmp_path / "is_sycophantic.joblib").exists()


def test_probes_available_false_when_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.probes.scorer.PROBES_DIR", tmp_path)
    # Clear functools.cache
    score_with_probes.cache_clear() if hasattr(score_with_probes, "cache_clear") else None
    from app.services.probes import scorer as _scorer

    _scorer._load_probes.cache_clear()
    assert probes_available() is False


def test_score_with_probes_returns_empty_when_no_probes(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.probes.scorer.PROBES_DIR", tmp_path)
    from app.services.probes import scorer as _scorer

    _scorer._load_probes.cache_clear()

    # No need to patch extractor — when no probes exist, scorer short-circuits
    # before calling extract_activations.
    scores = score_with_probes("diff", "review")
    assert isinstance(scores, ProbeScores)
    assert scores.is_sycophantic is None
