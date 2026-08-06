"""Export the live API's responses to static JSON for the S3/CloudFront build.

Run this while the Railway backend is still up — it is the only source of the
probe-scored runs, and they cannot be regenerated off Apple Silicon.

    python3 scripts/export_static_data.py

Writes frontend/public/data/ and mirrors it to ~/llm-eval-data-backup/.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from itertools import permutations
from pathlib import Path
from typing import Any

BASE = os.environ.get(
    "EXPORT_BASE_URL",
    "https://llm-eval-with-probes-production.up.railway.app",
).rstrip("/")

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "frontend" / "public" / "data"
BACKUP_DIR = Path(os.environ.get("EXPORT_BACKUP_DIR", Path.home() / "llm-eval-data-backup"))

# Hardcoded in frontend/src/pages/Compare.tsx. The compare view opens on this
# pair, so its file has to exist or the page breaks on first load.
FEATURED_PAIR = (
    "da6cbf86-bf65-4383-9280-751a539bd3c9",
    "09572347-d7d3-4a20-9709-8416b32657e5",
)

TIMEOUT = 60


def fetch(path: str) -> Any:
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        if resp.status != 200:
            raise RuntimeError(f"{url} returned HTTP {resp.status}")
        return json.load(resp)


def write(name: str, payload: Any) -> int:
    path = OUT_DIR / name
    text = json.dumps(payload, indent=2, sort_keys=True)
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def preflight() -> None:
    try:
        health = fetch("/health")
    except urllib.error.URLError as exc:
        sys.exit(
            f"cannot reach {BASE}: {exc}\n"
            "the backend must be alive for this export — stop and check it "
            "before deleting anything."
        )
    print(f"backend reachable: {BASE} -> {health}")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    preflight()

    runs = fetch("/runs?limit=50")
    if not isinstance(runs, list) or not runs:
        sys.exit(f"expected a non-empty run list, got: {type(runs).__name__}")
    write("runs.json", runs)
    ids = [r["id"] for r in runs]
    print(f"runs.json: {len(ids)} runs")

    files = 1
    for rid in ids:
        write(f"run_{rid}.json", fetch(f"/runs/{rid}"))
        write(f"disagreements_{rid}.json", fetch(f"/runs/{rid}/disagreements"))
        files += 2
        probes = (runs[ids.index(rid)].get("summary") or {}).get("probes")
        marker = "probes" if probes else "no probes"
        print(f"  {rid}  {marker}")

    # Every ordered pair, so the compare pickers work for any selection rather
    # than only the featured one.
    for a, b in permutations(ids, 2):
        write(f"compare_{a}_{b}.json", fetch(f"/runs/compare/{a}/{b}"))
        files += 1
    print(f"compare files: {len(ids) * (len(ids) - 1)}")

    missing = [r for r in FEATURED_PAIR if r not in ids]
    if missing:
        print(
            f"\nWARNING: featured pair id(s) not present in the run list: {missing}\n"
            "the compare page defaults to these; Compare.tsx needs updating.",
            file=sys.stderr,
        )
    else:
        print(f"featured pair present: {FEATURED_PAIR[0]} vs {FEATURED_PAIR[1]}")

    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    shutil.copytree(OUT_DIR, BACKUP_DIR)
    backup_count = len(list(BACKUP_DIR.glob("*.json")))
    total_bytes = sum(f.stat().st_size for f in OUT_DIR.glob("*.json"))

    print(
        f"\nwrote {files} json files ({total_bytes / 1_000_000:.2f} MB) to {OUT_DIR}"
        f"\nbacked up {backup_count} files to {BACKUP_DIR}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
