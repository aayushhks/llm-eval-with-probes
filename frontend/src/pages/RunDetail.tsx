import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  type DisagreementItem,
  type DisagreementResponse,
  type RunDetail as RunDetailType,
} from "../lib/api";
import { Badge } from "../components/Badge";
import { ScoreBar } from "../components/ScoreBar";
import { FlagPill } from "../components/FlagPill";

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<RunDetailType | null>(null);
  const [dis, setDis] = useState<DisagreementResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([api.getRun(id), api.getDisagreements(id)])
      .then(([r, d]) => {
        setRun(r);
        setDis(d);
      })
      .catch((e) => setError(String(e)));
  }, [id]);

  if (error) {
    return (
      <div className="text-rose-700 bg-rose-50 border border-rose-200 rounded p-4">
        Couldn't load run: {error}
      </div>
    );
  }
  if (!run || !dis) {
    return <div className="text-zinc-500">Loading…</div>;
  }

  // Defensive: older runs may not have summary populated
  if (!run.summary || typeof run.summary.passed !== "number") {
    return (
      <div className="text-amber-700 bg-amber-50 border border-amber-200 rounded p-4">
        This run is missing summary data. Likely a failed or pre-M3 run.
        <Link to="/" className="block text-sky-700 underline mt-2">
          ← back
        </Link>
      </div>
    );
  }

  const judge = run.summary?.judge;
  const probes = run.summary?.probes;
  const hasProbes =
    probes &&
    Object.values(probes).some((p) => p.mean !== null && p.n > 0);

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link to="/" className="text-sm text-sky-700 hover:underline">
            ← all runs
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight mt-2">
            Run {run.prompt_version}
          </h1>
          <div className="text-sm text-zinc-500 mt-1 font-mono">{run.id}</div>
        </div>
        <Link
          to={`/compare?a=${run.id}`}
          className="text-sm bg-zinc-900 text-white rounded-md px-3 py-2 hover:bg-zinc-800"
        >
          compare with…
        </Link>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard label="model" value={run.model} mono />
        <SummaryCard
          label="deterministic"
          value={`${run.summary.passed}/${run.summary.total}`}
          sub={`${Math.round(run.summary.pass_rate * 100)}%`}
        />
        <SummaryCard
          label="judge mean"
          value={judge ? `${judge.mean_quality.toFixed(2)}/10` : "—"}
          sub={
            judge
              ? `${Math.round(judge.pct_appropriately_skeptical * 100)}% skeptical`
              : undefined
          }
        />
        <SummaryCard
          label="probes"
          value={hasProbes ? "active" : "off"}
          sub={hasProbes ? "4 dimensions" : undefined}
        />
      </div>

      {/* Disagreements — the headline section */}
      <section>
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-lg font-semibold tracking-tight">
            Disagreements
          </h2>
          <span className="text-sm text-zinc-500">
            {dis.flagged_cases} of {dis.total_cases} cases flagged
          </span>
        </div>

        {dis.disagreements.length === 0 ? (
          <div className="text-sm text-zinc-500 bg-white border border-zinc-200 rounded p-4">
            No disagreements — all three scorers agree on every case.
          </div>
        ) : (
          <div className="space-y-3">
            {dis.disagreements.map((d) => (
              <DisagreementCard key={d.case_id} item={d} />
            ))}
          </div>
        )}
      </section>

      {/* Per-subset breakdown */}
      <section>
        <h2 className="text-lg font-semibold tracking-tight mb-4">
          By subset
        </h2>
        <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 text-zinc-500 text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-4 py-3">subset</th>
                <th className="text-right px-4 py-3">passed</th>
                <th className="text-right px-4 py-3">total</th>
                <th className="text-right px-4 py-3">pass rate</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(run.summary.by_subset).map(([name, stats]) => (
                <tr key={name} className="border-t border-zinc-100">
                  <td className="px-4 py-3 font-medium">{name}</td>
                  <td className="px-4 py-3 text-right">{stats.passed}</td>
                  <td className="px-4 py-3 text-right">{stats.total}</td>
                  <td className="px-4 py-3 text-right">
                    <Badge
                      tone={
                        stats.passed / stats.total >= 0.7
                          ? "good"
                          : stats.passed / stats.total >= 0.4
                          ? "warn"
                          : "bad"
                      }
                    >
                      {Math.round((stats.passed / stats.total) * 100)}%
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* All cases — compact table */}
      <section>
        <h2 className="text-lg font-semibold tracking-tight mb-4">
          All cases
        </h2>
        <div className="bg-white border border-zinc-200 rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 text-zinc-500 text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-3 py-3">case</th>
                <th className="text-left px-3 py-3">subset</th>
                <th className="text-center px-3 py-3">det</th>
                <th className="text-center px-3 py-3">judge</th>
                <th className="text-center px-3 py-3">syco</th>
                <th className="text-center px-3 py-3">uncert</th>
                <th className="text-center px-3 py-3">ungrnd</th>
                <th className="text-center px-3 py-3">refuse</th>
              </tr>
            </thead>
            <tbody>
              {run.cases.map((c) => (
                <tr key={c.case_id} className="border-t border-zinc-100">
                  <td className="px-3 py-2 font-mono text-xs">
                    {c.case_id}
                  </td>
                  <td className="px-3 py-2 text-zinc-500">{c.subset}</td>
                  <td className="px-3 py-2 text-center">
                    {c.passed ? (
                      <Badge tone="good">pass</Badge>
                    ) : (
                      <Badge tone="bad">fail</Badge>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {c.judge?.quality_score != null ? (
                      <Badge
                        tone={
                          c.judge.quality_score >= 7
                            ? "good"
                            : c.judge.quality_score >= 5
                            ? "warn"
                            : "bad"
                        }
                      >
                        {c.judge.quality_score}/10
                      </Badge>
                    ) : (
                      <span className="text-zinc-300">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center font-mono text-xs">
                    {formatScore(c.probes?.is_sycophantic ?? null)}
                  </td>
                  <td className="px-3 py-2 text-center font-mono text-xs">
                    {formatScore(c.probes?.is_uncertain ?? null)}
                  </td>
                  <td className="px-3 py-2 text-center font-mono text-xs">
                    {formatScore(c.probes?.is_ungrounded ?? null)}
                  </td>
                  <td className="px-3 py-2 text-center font-mono text-xs">
                    {formatScore(c.probes?.is_refusing ?? null)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function DisagreementCard({ item }: { item: DisagreementItem }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <div className="font-mono text-sm font-medium text-zinc-900">
            {item.case_id}
          </div>
          <div className="text-xs text-zinc-500 mt-0.5">
            {item.subset} · priority {item.priority}
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <div>
            <span className="text-zinc-400">det </span>
            <Badge tone={item.deterministic_passed ? "good" : "bad"}>
              {item.deterministic_passed ? "pass" : "fail"}
            </Badge>
          </div>
          <div>
            <span className="text-zinc-400">judge </span>
            {item.judge_quality !== null ? (
              <Badge
                tone={
                  item.judge_quality >= 7
                    ? "good"
                    : item.judge_quality >= 5
                    ? "warn"
                    : "bad"
                }
              >
                {item.judge_quality}/10
              </Badge>
            ) : (
              <span className="text-zinc-300">—</span>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {item.flags.map((f) => (
          <FlagPill key={f} flag={f} />
        ))}
      </div>

      <div className="grid grid-cols-2 gap-2 mb-3">
        <ScoreBar
          value={item.probes.is_sycophantic}
          tone="syco"
          label="syco"
        />
        <ScoreBar
          value={item.probes.is_uncertain}
          tone="uncert"
          label="uncert"
        />
        <ScoreBar
          value={item.probes.is_ungrounded}
          tone="ungrnd"
          label="ungrnd"
        />
        <ScoreBar
          value={item.probes.is_refusing}
          tone="refuse"
          label="refuse"
        />
      </div>

      <button
        onClick={() => setExpanded((e) => !e)}
        className="text-xs text-sky-700 hover:underline"
      >
        {expanded ? "hide" : "show"} model review + judge reasoning
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 text-xs">
          {item.judge_reasoning && (
            <div>
              <div className="text-zinc-400 mb-1">judge reasoning</div>
              <div className="text-zinc-700 leading-relaxed">
                {item.judge_reasoning}
              </div>
            </div>
          )}
          {item.raw_review && (
            <div>
              <div className="text-zinc-400 mb-1">model review (raw)</div>
              <pre className="bg-zinc-50 border border-zinc-200 rounded p-3 overflow-x-auto whitespace-pre-wrap text-zinc-700">
                {item.raw_review}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  sub,
  mono,
}: {
  label: string;
  value: string;
  sub?: string;
  mono?: boolean;
}) {
  return (
    <div className="bg-white border border-zinc-200 rounded-lg p-4">
      <div className="text-xs text-zinc-500 uppercase tracking-wider">
        {label}
      </div>
      <div
        className={`text-lg font-medium mt-1 ${mono ? "font-mono text-sm" : ""}`}
      >
        {value}
      </div>
      {sub && <div className="text-xs text-zinc-500 mt-0.5">{sub}</div>}
    </div>
  );
}

function formatScore(v: number | null): string {
  return v === null ? "—" : v.toFixed(2);
}