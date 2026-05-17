"""Train all probing classifiers. Run once, takes ~2-5 minutes on M4 Pro.

Usage:
    cd backend && uv run python ../scripts/train_probes.py && cd ..
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.logging import configure_logging  # noqa: E402
from app.services.probes.trainer import train_all  # noqa: E402


def main() -> int:
    configure_logging("INFO")
    print("Training probes — this loads Qwen2.5-3B-Instruct via MLX")
    print("(first run downloads ~2 GB of weights to ~/.cache/huggingface)\n")
    train_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())