import { useEffect, useState } from "react";
export interface GoldenCase {
  id: string;
  description: string;
  diff: string;
  should_approve: boolean;
  expected_issues: {
    must_mention: string[];
    min_severity: string;
    category?: string;
  }[];
  forbidden_keywords: string[];
  notes: string;
}
export interface Evidence {
  candidate_dataset: { total_cases: number; new_cases: number; status: string };
  repeat_report: { status: string; summary?: Record<string, unknown> } | null;
  unique_probe_disagreements: Record<string, number>;
  cases: GoldenCase[];
  probe_audit: {
    name: string;
    examples: number;
    positive: number;
    diff_groups: number;
    status: string;
    validation: {
      coverage: number;
      metrics: Record<string, unknown> | null;
    } | null;
  }[];
  threshold_note: string;
  flag_thresholds: Record<string, number>;
  run_counts: Record<string, number>;
  repeated_experiments: { status: string; reason: string };
}
let evidenceRequest: Promise<Evidence> | undefined;
export function getEvidence(): Promise<Evidence> {
  return (evidenceRequest ??= fetch("/data/evidence.json")
    .then((r) => {
      if (!r.ok) throw new Error("Evidence could not be loaded");
      return r.json() as Promise<Evidence>;
    })
    .catch((e) => {
      evidenceRequest = undefined;
      throw e;
    }));
}

export default function CaseEvidence({
  caseId,
  runId,
}: {
  caseId: string;
  runId: string;
}) {
  const [item, setItem] = useState<GoldenCase>();
  const [error, setError] = useState("");
  const [notes, setNotes] = useState("");
  const [verdict, setVerdict] = useState("needs_review");
  const [saved, setSaved] = useState(false);
  const key = `interp-eval-review:${runId}:${caseId}`;
  useEffect(() => {
    let active = true;
    setNotes("");
    setVerdict("needs_review");
    setSaved(false);
    getEvidence()
      .then((d) => {
        if (active) setItem(d.cases.find((c) => c.id === caseId));
      })
      .catch((e) => {
        if (active) setError(String(e));
      });
    try {
      const v = JSON.parse(localStorage.getItem(key) || "null");
      if (v) {
        setNotes(v.notes);
        setVerdict(v.verdict);
        setSaved(true);
      }
    } catch {
      setError("Saved review could not be read.");
    }
    return () => {
      active = false;
    };
  }, [key, caseId]);
  function record() {
    return {
      schema_version: 1,
      run_id: runId,
      case_id: caseId,
      verdict,
      notes,
      source: "user_entered_browser_annotation",
      updated_at: new Date().toISOString(),
    };
  }
  function save() {
    try {
      localStorage.setItem(key, JSON.stringify(record()));
      setSaved(true);
      setError("");
    } catch {
      setError(
        "Browser storage is unavailable. Export your review to keep it.",
      );
    }
  }
  function download() {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(record(), null, 2)], {
        type: "application/json",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `review-${caseId}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <section className="case-evidence">
      <h3>Input & expected behavior</h3>
      {error && <p role="alert">{error}</p>}
      {item ? (
        <>
          <p>{item.description}</p>
          <pre>{item.diff}</pre>
          <p>
            <strong>Expected approval:</strong>{" "}
            {item.should_approve ? "Approve" : "Do not approve"}
          </p>
          <ul>
            {item.expected_issues.map((x, i) => (
              <li key={i}>
                Expected issue terms: {x.must_mention.join(" / ")} · minimum
                severity: {x.min_severity}
                {x.category ? ` · ${x.category}` : ""}
              </li>
            ))}
          </ul>
          {item.forbidden_keywords.length > 0 && (
            <p>
              Disallowed terms in the rule scorer:{" "}
              {item.forbidden_keywords.join(", ")}
            </p>
          )}
          {item.notes && <p>Dataset note: {item.notes}</p>}
          <p className="evidence-caution">
            These are the benchmark’s expectations, not an independent human
            judgment. Keyword rules can miss paraphrases or over-penalize
            wording.
          </p>
        </>
      ) : (
        <p>Loading case evidence…</p>
      )}
      <div className="review-form">
        <h3>Your assessment</h3>
        <p>
          Inspect the diff, model review, and judge reasoning before choosing a
          verdict. Notes stay in this browser; they are not published or
          included in benchmark metrics.
        </p>
        <label>
          Review verdict
          <select
            value={verdict}
            onChange={(e) => {
              setVerdict(e.target.value);
              setSaved(false);
            }}
          >
            <option value="needs_review">Not reviewed / unsure</option>
            <option value="model_failure">
              Model review contains a real failure
            </option>
            <option value="scorer_error">Scorer flagged a valid review</option>
            <option value="ambiguous">Ambiguous expectations</option>
          </select>
        </label>
        <label>
          Reasoning
          <textarea
            value={notes}
            onChange={(e) => {
              setNotes(e.target.value);
              setSaved(false);
            }}
            placeholder="Point to the code and explain which scorer you agree with, and why."
            rows={3}
          />
        </label>
        <div>
          <button onClick={save}>Save assessment</button>
          <button onClick={download}>Export assessment JSON</button>
          <span role="status">{saved ? "Saved in this browser" : ""}</span>
        </div>
      </div>
    </section>
  );
}
