import importlib.util
from pathlib import Path

import numpy as np
import pytest

from app.services.eval.repeats import summarize_pairs
from app.services.probes.validation import diff_group, validate_features


def test_grouped_validation_never_trains_on_held_out_diff():
    # Synthetic fixtures test the protocol, not actual probe performance.
    y = np.tile([0, 1], 6)
    X = np.column_stack([y * 10, np.zeros(len(y))])
    groups = [f"diff-{i // 2}" for i in range(len(y))]
    result = validate_features(X, y, groups)
    assert result["coverage"] == 1
    assert result["metrics"]["accuracy"] == 1
    for fold in result["folds"]:
        assert fold["held_out_group"] not in fold["train_groups"]


def test_single_class_training_fold_does_not_become_performance_claim():
    r = validate_features(
        np.array([[0], [1], [2], [3]]), np.array([0, 0, 1, 1]), ["a", "a", "b", "b"]
    )
    assert r["coverage"] == 0
    assert r["metrics"] is None
    assert r["status"] == "incomplete_group_coverage"


def test_whitespace_variants_are_same_group():
    assert diff_group("a b\nc") == diff_group("a  b c")


def test_repeats_reject_recounting_same_run():
    pair = {
        "a": {"id": "a", "total": 20, "pass_rate": 0.4},
        "b": {"id": "b", "total": 20, "pass_rate": 0.5},
    }
    with pytest.raises(ValueError):
        summarize_pairs([pair, pair])
    assert summarize_pairs([pair])["interval_95"] is None


def test_paired_round_interval():
    pairs = [
        {
            "a": {"id": f"a{i}", "total": 20, "pass_rate": 0.4},
            "b": {"id": f"b{i}", "total": 20, "pass_rate": rate},
        }
        for i, rate in enumerate([0.4, 0.5, 0.6])
    ]
    r = summarize_pairs(pairs)
    assert r["mean_pass_rate_delta"] == pytest.approx(0.1)
    assert r["interval_95"][0] < 0.1 < r["interval_95"][1]


def test_evidence_matches_actual_sources():
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "build_evidence", root / "scripts/build_evidence.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    d = mod.build()
    assert len(d["cases"]) == 20
    assert sum(p["examples"] for p in d["probe_audit"]) == 42
    assert d["run_counts"] == {"v1": 1, "v2": 1}
    assert d["unique_probe_disagreements"]["v1"] == 5


def test_candidate_dataset_preserves_original_cases():
    from collections import Counter

    from app.datasets.loader import load_dataset

    root = Path(__file__).resolve().parents[2]
    original = load_dataset(root / "datasets/code_review/golden_v1.jsonl")
    candidate = load_dataset(root / "datasets/code_review/candidate_v2.jsonl")
    assert candidate[:20] == original
    assert len(candidate) == 30
    assert set(c.id for c in candidate[20:]).isdisjoint(c.id for c in original)
    assert set(Counter(c.subset for c in candidate[20:]).values()) == {2}
    assert all("pending_human_review" in c.tags for c in candidate[20:])
