"""Publication-quality figures for eval runs.

Style choices:
- Sans-serif, large fonts (readable in slides + arXiv)
- Color palette is colorblind-safe
- Saved as both PNG (for slides) and SVG (for vector use)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from app.services.analysis.disagreement import CaseRow

# Style
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 120,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    }
)

# Colorblind-safe palette (Wong 2011)
_BLUE = "#0072B2"
_ORANGE = "#E69F00"
_GREEN = "#009E73"
_RED = "#D55E00"
_GRAY = "#999999"


@dataclass
class FigurePaths:
    png: Path
    svg: Path


def _save_both(fig: Figure, out_dir: Path, name: str) -> FigurePaths:
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{name}.png"
    svg = out_dir / f"{name}.svg"
    fig.savefig(png)
    fig.savefig(svg)
    plt.close(fig)
    return FigurePaths(png=png, svg=svg)


def probe_vs_judge_scatter(rows: Sequence[CaseRow], out_dir: Path) -> FigurePaths:
    """Scatter: x = judge quality, y = probe sycophantic score.

    Points in the upper-right are *disagreements* — judge says the review is
    good, but the probe detects sycophancy in the model's hidden states.
    """
    fig, ax = plt.subplots(figsize=(6.5, 4.5))

    judge_list: list[int] = []
    syco_list: list[float] = []
    det_pass_list: list[bool] = []
    case_ids: list[str] = []
    for r in rows:
        if r.judge_quality is None or r.probe_sycophantic is None:
            continue
        judge_list.append(r.judge_quality)
        syco_list.append(r.probe_sycophantic)
        det_pass_list.append(r.deterministic_passed)
        case_ids.append(r.case_id)

    judge = np.array(judge_list)
    syco = np.array(syco_list)
    det_pass = np.array(det_pass_list)

    pass_mask = det_pass
    fail_mask = ~det_pass

    ax.scatter(
        judge[pass_mask],
        syco[pass_mask],
        c=_GREEN,
        s=80,
        edgecolor="white",
        label="deterministic: pass",
        zorder=3,
    )
    ax.scatter(
        judge[fail_mask],
        syco[fail_mask],
        c=_RED,
        s=80,
        edgecolor="white",
        marker="s",
        label="deterministic: fail",
        zorder=3,
    )

    # Shaded "disagreement zone" — judge thinks it's good, probe says sycophantic
    ax.axvspan(7, 10.5, ymin=0.3, color=_ORANGE, alpha=0.12, zorder=1)
    ax.text(
        8.75,
        0.95,
        "disagreement zone",
        fontsize=10,
        color="#666",
        ha="center",
        va="top",
        style="italic",
    )

    # Annotate the most striking disagreements
    short_name = {
        "clear_003_bare_except": "clear_003",
        "syco_003_tests_that_dont_test": "syco_003",
        "bug_003_iterator_consumed_twice": "bug_003",
        "bug_004_dict_during_iteration": "bug_004",
        "ground_004_diff_only_whitespace": "ground_004",
    }
    for x, y, name in zip(judge, syco, case_ids, strict=True):
        if x >= 7 and y >= 0.30:
            ax.annotate(
                short_name.get(name, name),
                xy=(x, y),
                xytext=(10, -2),
                textcoords="offset points",
                fontsize=9,
                color="#222",
                fontweight="bold",
            )

    ax.set_xlim(-0.5, 11.2)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("LLM-as-judge quality score (0–10)")
    ax.set_ylabel("Probe: P(sycophantic)")
    ax.set_title("Probe-vs-judge disagreement on the code-review task")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    return _save_both(fig, out_dir, "probe_vs_judge_scatter")


def per_subset_scorer_comparison(
    rows_v1: Sequence[CaseRow],
    rows_v2: Sequence[CaseRow],
    out_dir: Path,
) -> FigurePaths:
    """Grouped bar chart: deterministic pass rate by subset for v1 vs v2."""
    fig, ax = plt.subplots(figsize=(7, 4.5))

    subsets = ["clean", "clear_issues", "sycophancy_bait", "grounding_bait", "subtle_bugs"]
    v1_pct = [_pass_rate(rows_v1, s) for s in subsets]
    v2_pct = [_pass_rate(rows_v2, s) for s in subsets]

    x = np.arange(len(subsets))
    w = 0.38
    ax.bar(x - w / 2, v1_pct, w, label="v1 (baseline)", color=_BLUE)
    ax.bar(x + w / 2, v2_pct, w, label="v2 (anti-sycophancy)", color=_ORANGE)

    for xi, val in zip(x - w / 2, v1_pct, strict=True):
        ax.text(xi, val + 0.02, f"{val:.0%}", ha="center", fontsize=9)
    for xi, val in zip(x + w / 2, v2_pct, strict=True):
        ax.text(xi, val + 0.02, f"{val:.0%}", ha="center", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(subsets, rotation=20, ha="right")
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("deterministic pass rate")
    ax.set_title("v1 vs v2 prompt: per-subset deterministic pass rate")
    ax.legend(frameon=False)
    fig.tight_layout()
    return _save_both(fig, out_dir, "per_subset_pass_rate_v1_vs_v2")


def _pass_rate(rows: Sequence[CaseRow], subset: str) -> float:
    in_subset = [r for r in rows if r.subset == subset]
    if not in_subset:
        return 0.0
    return sum(1 for r in in_subset if r.deterministic_passed) / len(in_subset)


def scorer_agreement_heatmap(rows: Sequence[CaseRow], out_dir: Path) -> FigurePaths:
    """Heatmap: per-case agreement among the three scorers.

    Rows = cases, columns = (deterministic, judge, sycophancy probe).
    Cell intensity = "thinks this review is good" (1 = good).
    """
    cells = []
    case_ids = []
    for r in rows:
        if r.judge_quality is None or r.probe_sycophantic is None:
            continue
        det_good = 1.0 if r.deterministic_passed else 0.0
        judge_good = (r.judge_quality / 10.0) if r.judge_quality is not None else 0.5
        probe_good = 1.0 - (r.probe_sycophantic or 0.0)
        cells.append([det_good, judge_good, probe_good])
        case_ids.append(r.case_id)

    arr = np.array(cells)
    fig, ax = plt.subplots(figsize=(6.5, max(4, len(case_ids) * 0.28)))
    im = ax.imshow(arr, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(3))
    ax.set_xticklabels(
        ["deterministic", "judge (norm.)", "1 − P(syco)"],
        rotation=20,
        ha="right",
        fontsize=10,
    )
    ax.set_yticks(range(len(case_ids)))
    ax.set_yticklabels(case_ids, fontsize=8)
    ax.set_title("Scorer agreement: green = thinks review is good")
    fig.colorbar(im, ax=ax, fraction=0.04, pad=0.04)
    fig.tight_layout()
    return _save_both(fig, out_dir, "scorer_agreement_heatmap")
