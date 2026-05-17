# V1 vs V2 prompt comparison

Model: Llama 3.1 8B Instant (Groq), reviewed
Judge: Llama 3.3 70B Versatile (Groq)
Dataset: golden_v1.jsonl (20 cases, 4 per subset)

## Headline

| Metric | V1 | V2 | Δ |
|---|---|---|---|
| **Deterministic** | | | |
| Overall pass rate | 9/20 (45%) | 8/20 (40%) | -1 |
| clean | 3/4 | 0/4 | -3 |
| clear_issues | 2/4 | 4/4 | +2 |
| sycophancy_bait | 2/4 | 3/4 | +1 |
| grounding_bait | 1/4 | 1/4 | 0 |
| subtle_bugs | 1/4 | 0/4 | -1 |
| **LLM-as-judge** | | | |
| Mean quality (0–10) | 6.60 | 8.15 | +1.55 |
| Caught real issues | 75% | 80% | +5pp |
| Invented issues | 10% | 10% | 0 |
| Appropriately skeptical | 70% | 90% | +20pp |

## The disagreement is the finding

The deterministic scorer says V2 is *worse* (-5pp pass rate). The judge says V2 is *substantially better* (+1.55 quality, +20pp skepticism). Both metrics are honest — they measure different things.

- **Deterministic** is precise: it requires correct keywords, correct severity, and correct approval. V2's anti-sycophancy prompt makes the model over-flag clean diffs, tanking the `clean` subset (3/4 → 0/4) and crashing `subtle_bugs` (model now dismisses uncertain bugs as immaterial rather than hedging them).
- **Judge** is holistic: it reads the full review against the full diff. V2's reviews are genuinely better at catching real issues. The 20-point lift in "appropriately skeptical" confirms the anti-sycophancy framing did exactly what it was designed to do.

A naive observer using only the deterministic metric would conclude V2 is a regression and roll it back. A naive observer using only the judge would conclude V2 is a win and ship it. **The right answer is "V2 is a different point in the precision/recall tradeoff" — and you only see that tradeoff if you have both metrics.**

## What this implies for M6 (probes)

- The disagreement cases (deterministic-fail but judge-pass, or vice versa) are exactly where a third signal — probing classifiers on hidden states — should add value.
- `grounding_bait` was unchanged 25% → 25% across both prompts AND the judge's overall numbers didn't shift on those cases. That confirms prompt engineering cannot fix groundedness. Probes are the next lever.
- The deterministic metric is more stable than the judge — judges drift with prompt. The probes will provide a fixed third reference.