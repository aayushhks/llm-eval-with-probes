"""Extract residual-stream activations from Qwen2.5-3B-Instruct via MLX.

Design notes:
- We use a fixed middle layer (14 of 36) — empirically the best layer for
  semantic features in 3B-class models.
- We mean-pool across the prompt tokens (excluding the system prompt).
- Output: 2048-dim numpy float32 vector per prompt.
"""

from __future__ import annotations

import functools
from typing import Any

import mlx.core as mx
import numpy as np
from mlx_lm import load
from mlx_lm.tokenizer_utils import TokenizerWrapper

from app.core.logging import get_logger

logger = get_logger("probes.extractor")

PROBE_LAYER = 14  # middle layer of Qwen2.5-3B (36 layers total)
DEFAULT_MODEL = "mlx-community/Qwen2.5-3B-Instruct-4bit"


@functools.cache
def _load_model(model_name: str) -> tuple[Any, TokenizerWrapper]:
    """Load model + tokenizer once. Cached for the process lifetime."""
    logger.info("loading_mlx_model", model=model_name)
    result = load(model_name)
    # mlx-lm versions return either (model, tokenizer) or (model, tokenizer, _)
    model, tokenizer = result[0], result[1]
    return model, tokenizer


def _build_prompt(diff: str, model_review: str) -> str:
    """The probe sees a chat-style transcript: the original task + the model's review.

    We probe representations of the *combined* context because that's what
    captures behavior-in-context (e.g. "did this model just produce a
    sycophantic answer to this diff").
    """
    return (
        "<|im_start|>system\nYou review code diffs.<|im_end|>\n"
        f"<|im_start|>user\nReview this diff:\n\n{diff}<|im_end|>\n"
        f"<|im_start|>assistant\n{model_review}<|im_end|>"
    )


def extract_activations(
    diff: str,
    model_review: str,
    model_name: str = DEFAULT_MODEL,
    layer: int = PROBE_LAYER,
) -> np.ndarray:
    """Return mean-pooled residual stream activations at the given layer.

    Output shape: (hidden_dim,) float32. For Qwen2.5-3B, hidden_dim = 2048.
    """
    model, tokenizer = _load_model(model_name)

    prompt = _build_prompt(diff, model_review)
    tokens = mx.array(tokenizer.encode(prompt))[None]  # add batch dim

    # Forward pass with intermediate states. mlx-lm's `model(...)` returns the
    # logits; we monkey-patch by capturing via hooks. Simplest robust approach:
    # use `model.model.layers[: layer + 1]` manually.
    h = model.model.embed_tokens(tokens)
    for i in range(layer + 1):
        h = model.model.layers[i](h, mask=None, cache=None)
        # Some MLX implementations return a tuple
        if isinstance(h, tuple):
            h = h[0]
    mx.eval(h)  # materialize

    # h: (1, seq_len, hidden_dim) — mean-pool across sequence
    activations: np.ndarray = np.asarray(h, dtype=np.float32).mean(axis=1).squeeze()
    return activations
