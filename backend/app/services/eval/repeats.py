"""Summarize paired rounds. A bootstrap over cases is not a repeat experiment."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import t


def summarize_pairs(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [run[arm]["id"] for run in rounds for arm in ("a", "b")]
    if len(ids) != len(set(ids)):
        raise ValueError("A run cannot be counted as multiple independent measurements")
    for pair in rounds:
        if pair["a"]["total"] != pair["b"]["total"]:
            raise ValueError("Paired runs must cover the same number of cases")
    deltas = np.array([r["b"]["pass_rate"] - r["a"]["pass_rate"] for r in rounds])
    interval = None
    if len(deltas) >= 3:
        half = float(t.ppf(0.975, len(deltas) - 1) * deltas.std(ddof=1) / np.sqrt(len(deltas)))
        interval = [float(deltas.mean() - half), float(deltas.mean() + half)]
    return {
        "n_pairs": len(rounds),
        "mean_pass_rate_delta": float(deltas.mean()) if len(deltas) else None,
        "paired_round_deltas": deltas.tolist(),
        "interval_95": interval,
        "interval_method": (
            "Student t interval across paired rounds; "
            "same fixed dataset, not unseen-task generalization"
        ),
        "status": "repeated" if len(rounds) >= 3 else "insufficient_repeats",
    }
