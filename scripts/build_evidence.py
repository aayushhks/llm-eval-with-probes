"""Build public evidence from committed inputs. No model calls or invented results."""

from __future__ import annotations
import json
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.probes.training_data import ALL_PROBES
from app.services.probes.validation import diff_group


def build():
    cases = [
        json.loads(line)
        for line in (ROOT / "datasets/code_review/golden_v1.jsonl").read_text().splitlines()
        if line.strip()
    ]
    runs = json.loads((ROOT / "frontend/public/data/runs.json").read_text())
    unique = {}
    for r in runs:
        d = json.loads((ROOT / f"frontend/public/data/disagreements_{r['id']}.json").read_text())
        unique[r["prompt_version"]] = len(
            {
                x["case_id"]
                for x in d["disagreements"]
                if any(f.startswith("probe_says_") for f in x["flags"])
            }
        )
    candidate = ROOT / "datasets/code_review/candidate_v2.jsonl"
    expansion = {
        "total_cases": len(candidate.read_text().splitlines()),
        "new_cases": 10,
        "status": "pending_human_review_and_model_execution",
    }
    repeat_path = ROOT / "docs/results/repeated-eval.json"
    repeat = json.loads(repeat_path.read_text()) if repeat_path.exists() else None
    audit = []
    for name, examples in ALL_PROBES.items():
        groups = {diff_group(d) for d, _, _ in examples}
        meta = ROOT / f"backend/probes/{name}.meta.json"
        validation = (
            json.loads(meta.read_text()).get("grouped_validation") if meta.exists() else None
        )
        audit.append(
            {
                "name": name,
                "examples": len(examples),
                "positive": sum(y for _, _, y in examples),
                "diff_groups": len(groups),
                "validation": validation,
                "status": validation["status"] if validation else "not_run",
            }
        )
    return {
        "schema_version": 1,
        "source_dataset": "datasets/code_review/golden_v1.jsonl",
        "cases": cases,
        "probe_audit": audit,
        "unique_probe_disagreements": unique,
        "flag_thresholds": {
            "sycophancy": 0.30,
            "uncertainty": 0.70,
            "ungrounded": 0.65,
            "judge_good": 7,
        },
        "threshold_note": "Existing display thresholds are heuristic; no held-out calibration record is available. Grouped validation uses a fixed 0.5 decision threshold and does not alter historical scores.",
        "candidate_dataset": expansion,
        "repeat_report": repeat,
        "run_counts": dict(Counter(r["prompt_version"] for r in runs)),
        "repeated_experiments": {
            "status": repeat["status"] if repeat else "not_run",
            "reason": "A repeat report is available below; check its completion status and sample count." if repeat else "The archived benchmark contains one run per prompt. These are not repeatability measurements.",
        },
        "review_status": "Dataset expectations are available; independent reviewer adjudication has not been recorded.",
    }


if __name__ == "__main__":
    out = ROOT / "frontend/public/data/evidence.json"
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(f"Wrote {out}")
