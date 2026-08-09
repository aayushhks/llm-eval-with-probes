// API client. All paths go through the vite proxy → http://localhost:8000

export interface RunSummary {
  total: number;
  passed: number;
  pass_rate: number;
  by_subset: Record<string, { passed: number; total: number }>;
  tokens: { prompt: number; completion: number };
  judge: {
    n_judged: number;
    mean_quality: number;
    pct_caught_real_issues: number;
    pct_invented_issues: number;
    pct_appropriately_skeptical: number;
    tokens: { prompt: number; completion: number };
  } | null;
  probes?: Record<string, { n: number; mean: number | null }>;
}

export interface RunListItem {
  id: string;
  prompt_version: string;
  model: string;
  provider: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  dataset_size: number;
  notes: string;
  summary: RunSummary;
}

export interface ProbeScores {
  is_sycophantic: number | null;
  is_refusing: number | null;
  is_ungrounded: number | null;
  is_uncertain: number | null;
}

export interface JudgeFields {
  quality_score: number | null;
  caught_real_issues: boolean | null;
  invented_issues: boolean | null;
  appropriately_skeptical: boolean | null;
  reasoning: string | null;
  parse_error: string | null;
  latency_ms: number | null;
  tokens: { prompt: number | null; completion: number | null };
}

export interface RunCase {
  case_id: string;
  subset: string;
  passed: boolean;
  approve_correct: boolean;
  issues_caught: number;
  issues_expected: number;
  forbidden_keyword_hits: string[];
  parse_error: string | null;
  latency_ms: number;
  tokens: { prompt: number; completion: number };
  judge: JudgeFields | null;
  probes: ProbeScores | null;
}

export interface RunDetail extends RunListItem {
  cases: RunCase[];
}

export interface DisagreementItem {
  case_id: string;
  subset: string;
  deterministic_passed: boolean;
  judge_quality: number | null;
  judge_reasoning: string | null;
  probes: ProbeScores;
  flags: string[];
  priority: number;
  raw_review: string | null;
}

export interface DisagreementResponse {
  run_id: string;
  prompt_version: string;
  model: string;
  total_cases: number;
  flagged_cases: number;
  flag_totals: Record<string, number>;
  disagreements: DisagreementItem[];
}

export interface CaseDiff {
  case_id: string;
  subset: string;
  deterministic: { a: boolean; b: boolean; change: string };
  judge: { a: number | null; b: number | null; delta: number | null; change: string };
  probes: {
    deltas: Record<string, number | null>;
    changes: Record<string, string>;
  };
  overall_change: string;
}

export interface CompareResponse {
  run_a: string;
  run_b: string;
  total_cases: number;
  summary: Record<string, number>;
  regressions: CaseDiff[];
  all_diffs: CaseDiff[];
}

// The deployed site is static: the runs are frozen, so every endpoint's
// response was exported to /data by scripts/export_static_data.py and is served
// as a plain file. Set VITE_STATIC_MODE=false to talk to a live backend instead
// (useful locally after running a fresh eval).
const STATIC_MODE = import.meta.env.VITE_STATIC_MODE !== "false";
const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";
const DATA_BASE = import.meta.env.VITE_DATA_BASE_URL || "/data";

async function http<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`);
  if (!resp.ok) {
    throw new Error(`API ${resp.status}: ${path}`);
  }
  return resp.json() as Promise<T>;
}

async function staticJson<T>(file: string): Promise<T> {
  const resp = await fetch(`${DATA_BASE}/${file}`);
  if (!resp.ok) {
    throw new StaticDataMissing(file);
  }
  // A bad status is not enough to spot a missing export: the SPA fallback
  // rewrites unknown paths to index.html and answers 200 with HTML, both under
  // vite preview and under CloudFront's 404 -> /index.html rule. Treat anything
  // that will not parse as JSON as missing rather than as a hard failure.
  const body = await resp.text();
  try {
    return JSON.parse(body) as T;
  } catch {
    throw new StaticDataMissing(file);
  }
}

// Thrown when a requested file was not part of the export. Callers can tell
// this apart from a genuine failure and show something softer than an error.
export class StaticDataMissing extends Error {
  readonly file: string;

  constructor(file: string) {
    super(`no pre-exported data for ${file}`);
    this.name = "StaticDataMissing";
    this.file = file;
  }
}

export const api = {
  // limit is honoured by the live API only — the export is already the full
  // frozen list, so there is nothing to trim client side.
  listRuns: (limit = 50) =>
    STATIC_MODE
      ? staticJson<RunListItem[]>("runs.json")
      : http<RunListItem[]>(`/runs?limit=${limit}`),
  getRun: (id: string) =>
    STATIC_MODE
      ? staticJson<RunDetail>(`run_${id}.json`)
      : http<RunDetail>(`/runs/${id}`),
  getDisagreements: (id: string) =>
    STATIC_MODE
      ? staticJson<DisagreementResponse>(`disagreements_${id}.json`)
      : http<DisagreementResponse>(`/runs/${id}/disagreements`),
  compareRuns: (a: string, b: string) =>
    STATIC_MODE
      ? staticJson<CompareResponse>(`compare_${a}_${b}.json`)
      : http<CompareResponse>(`/runs/compare/${a}/${b}`),
};