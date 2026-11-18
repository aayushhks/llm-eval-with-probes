# Validation protocol

## What changed

The UI now exposes the original case diff and benchmark expectations next to the generated review and judge explanation. Browser-local annotations record a verdict, rationale, run ID, case ID, and timestamp, and can be exported as JSON. The project does not manufacture reviewer identities or count unreviewed annotations as ground truth.

## Current evidence

The committed archive contains one v1 run and one v2 run over 20 cases. In v1, nine probe-versus-judge flags belong to five distinct cases. Summing behavior flags is not a case count. Flags identify candidates for inspection; they are not independent confirmation of a model failure.

The four probes contain 13, 11, 9, and 9 labeled training pairs. Their code diffs recur. Existing example-level cross-validation can therefore share code across train and test splits. It is retained as a clearly labeled legacy diagnostic for compatibility, not used as a generalization claim.

## New grouped protocol

`validation.py` leaves one whitespace-normalized code diff out at a time, refits logistic regression on the remaining groups, and predicts the held-out group. The fixed classification threshold is 0.5; it is not selected using held-out labels. It records group membership, coverage, out-of-fold probabilities, precision, recall, F1, accuracy, balanced accuracy, ROC AUC, Brier score, and a confusion matrix.

A fold with only one training class is skipped. If any examples lack out-of-fold predictions, aggregate metrics are withheld. The very small number of unique code diffs remains a limitation. Exact-diff grouping does not detect semantic duplicates, and these results would not establish performance on production reviews.

The current display cutoffs (0.30 sycophancy, 0.70 uncertainty, 0.65 ungrounded; judge >=7) are legacy heuristic thresholds, not calibrated decision boundaries. Historical scores and flags are unchanged.

## Repeats and expansion

The repeat CLI uses the existing real evaluation pipeline, persists runs, counterbalances prompt order, and checkpoints progress. Its dry-run mode does not call providers. Real runs require a configured database and Groq credentials. Probe scoring additionally requires trained model files and MLX on Apple Silicon. `--no-probes` must be explicitly selected for a rules/judge-only study.

The report records model names, prompt hashes, subject sampling settings, git revision and dirty state, dataset hash, case IDs, execution order, and distinct run IDs. It refuses to overwrite an existing report. A t interval over paired-round pass-rate differences is reported only after at least three completed pairs. These repeated measurements use a fixed benchmark; they do not estimate new-task generalization or remove provider/model drift.

The candidate v2 file adds ten AI-assisted draft cases across the five categories. Original cases remain byte-semantically unchanged. Review the new expectations before evaluating them. No real model execution, new held-out accuracy, or independent human adjudication has been performed in this update.

## Commands

From `backend/`:

```sh
uv run pytest -q
uv run python ../scripts/train_probes.py
uv run python ../scripts/build_evidence.py
uv run python ../scripts/run_repeated_eval.py --rounds 3
# Real API calls, after inspecting the dry-run plan:
uv run python ../scripts/run_repeated_eval.py --rounds 3 --execute
```

For an expanded-data study, supply `--dataset ../datasets/code_review/candidate_v2.jsonl` and a distinct `--output` path. Do not compare its aggregate score directly with the smaller benchmark as a prompt effect. Export the default report with `build_evidence.py` after completing an actual study.
