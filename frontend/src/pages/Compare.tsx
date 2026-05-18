import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  api,
  type CaseDiff,
  type CompareResponse,
  type RunListItem,
} from "../lib/api";
import { Badge } from "../components/Badge";

export default function Compare() {
  const [params, setParams] = useSearchParams();
  const a = params.get("a") || "";
  const b = params.get("b") || "";

  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [diff, setDiff] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listRuns(50).then(setRuns).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!a || !b) {
      setDiff(null);
      return;
    }
    setDiff(null);
    setError(null);
    api
      .compareRuns(a, b)
      .then(setDiff)
      .catch((e) => setError(String(e)));
  }, [a, b]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Compare runs</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Pick a baseline and a candidate. We diff per-case scores across all
          three scorers.
        </p>
      </div>

      <div className="bg-white border border-zinc-200 rounded-lg p-4 grid grid-cols-2 gap-4">
        <RunPicker
          label="baseline (A)"
          runs={runs}
          value={a}
          onChange={(v) => setParams({ a: v, b })}
        />
        <RunPicker
          label="candidate (B)"
          runs={runs}
          value={b}
          onChange={(v) => setParams({ a, b: v })}
        />
      </div>

      {error && (
        <div className="text-rose-700 bg-rose-50 border border-rose-200 rounded p-4">
          {error}
        </div>
      )}

      {a && b && !diff && !error && (
        <div className="text-zinc-500">Loading diff…</div>
      )}

      {diff && <DiffView diff={diff} />}

      {(!a || !b) && !error && (
        <div className="text-sm text-zinc-500 border border-dashed border-zinc-300 rounded p-6 text-center">
          Select both runs to see the diff.
        </div>
      )}
    </div>
  );
}

function RunPicker({
  label,
  runs,
  value,
  onChange,
}: {
  label: string;
  runs: RunListItem[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-xs text-zinc-500 uppercase tracking-wider">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full text-sm border border-zinc-200 rounded px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-sky-500"
      >
        <option value="">— select a run —</option>
        {runs.map((r) => (
          <option key={r.id} value={r.id}>
            {r.prompt_version} · {formatRunLabel(r)}
          </option>
        ))}
      </select>
    </label>
  );
}

function formatRunLabel(r: RunListItem): string {
  const d = new Date(r.started_at);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function DiffView({ diff }: { diff: CompareResponse }) {
  const s = diff.summary;
  const regressions = diff.all_diffs.filter((d) => d.overall_change === "regression");
  const mixed = diff.all_diffs.filter((d) => d.overall_change === "mixed");
  const improvements = diff.all_diffs.filter((d) => d.overall_change === "improvement");
  const unchanged = diff.all_diffs.filter((d) => d.overall_change === "unchanged");

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="regressions" value={s.regression ?? 0} tone="bad" />
        <StatCard label="mixed" value={s.mixed ?? 0} tone="warn" />
        <StatCard label="improvements" value={s.improvement ?? 0} tone="good" />
        <StatCard label="unchanged" value={s.unchanged ?? 0} tone="neutral" />
      </div>

      {regressions.length > 0 && (
        <DiffSection
          title="Regressions"
          subtitle="Cases that got worse in the candidate run"
          diffs={regressions}
        />
      )}
      {mixed.length > 0 && (
        <DiffSection
          title="Mixed"
          subtitle="Cases that improved on some scorers and regressed on others"
          diffs={mixed}
        />
      )}
      {improvements.length > 0 && (
        <DiffSection
          title="Improvements"
          subtitle="Cases that got better in the candidate run"
          diffs={improvements}
        />
      )}
      {unchanged.length > 0 && (
        <DiffSection
          title="Unchanged"
          subtitle="No material score change on any dimension"
          diffs={unchanged}
          dim
        />
      )}
    </div>
  );
}

function DiffSection({
  title,
  subtitle,
  diffs,
  dim = false,
}: {
  title: string;
  subtitle: string;
  diffs: CaseDiff[];
  dim?: boolean;
}) {
  return (
    <section>
      <div className="mb-3">
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        <p className="text-xs text-zinc-500 mt-0.5">{subtitle}</p>
      </div>
      <div className="bg-white border border-zinc-200 rounded-lg overflow-x-auto">
        <table className={`w-full text-sm ${dim ? "opacity-60" : ""}`}>
          <thead className="bg-zinc-50 text-zinc-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-3 py-3">case</th>
              <th className="text-left px-3 py-3">subset</th>
              <th className="text-center px-3 py-3">det</th>
              <th className="text-center px-3 py-3">judge</th>
              <th className="text-center px-3 py-3">syco Δ</th>
              <th className="text-center px-3 py-3">uncert Δ</th>
              <th className="text-center px-3 py-3">ungrnd Δ</th>
            </tr>
          </thead>
          <tbody>
            {diffs.map((d) => (
              <DiffRow key={d.case_id} d={d} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function DiffRow({ d }: { d: CaseDiff }) {
  return (
    <tr className="border-t border-zinc-100">
      <td className="px-3 py-2 font-mono text-xs">{d.case_id}</td>
      <td className="px-3 py-2 text-zinc-500">{d.subset}</td>
      <td className="px-3 py-2 text-center">
        <DetCell change={d.deterministic.change} a={d.deterministic.a} b={d.deterministic.b} />
      </td>
      <td className="px-3 py-2 text-center">
        <JudgeCell
          change={d.judge.change}
          a={d.judge.a}
          b={d.judge.b}
          delta={d.judge.delta}
        />
      </td>
      <td className="px-3 py-2 text-center">
        <ProbeDeltaCell
          delta={d.probes.deltas.is_sycophantic}
          change={d.probes.changes.is_sycophantic}
        />
      </td>
      <td className="px-3 py-2 text-center">
        <ProbeDeltaCell
          delta={d.probes.deltas.is_uncertain}
          change={d.probes.changes.is_uncertain}
        />
      </td>
      <td className="px-3 py-2 text-center">
        <ProbeDeltaCell
          delta={d.probes.deltas.is_ungrounded}
          change={d.probes.changes.is_ungrounded}
        />
      </td>
    </tr>
  );
}

function DetCell({
  change,
  a,
  b,
}: {
  change: string;
  a: boolean;
  b: boolean;
}) {
  if (change === "regression") {
    return <Badge tone="bad">pass → fail</Badge>;
  }
  if (change === "improvement") {
    return <Badge tone="good">fail → pass</Badge>;
  }
  return (
    <span className="text-zinc-400 text-xs font-mono">
      {a ? "pass" : "fail"} → {b ? "pass" : "fail"}
    </span>
  );
}

function JudgeCell({
  change,
  a,
  b,
  delta,
}: {
  change: string;
  a: number | null;
  b: number | null;
  delta: number | null;
}) {
  if (a === null || b === null) {
    return <span className="text-zinc-300">—</span>;
  }
  if (change === "regression") {
    return (
      <Badge tone="bad">
        {a} → {b} (Δ{delta})
      </Badge>
    );
  }
  if (change === "improvement") {
    return (
      <Badge tone="good">
        {a} → {b} (+{delta})
      </Badge>
    );
  }
  return (
    <span className="text-zinc-400 text-xs font-mono">
      {a} → {b}
    </span>
  );
}

function ProbeDeltaCell({
  delta,
  change,
}: {
  delta: number | null;
  change: string;
}) {
  if (delta === null) return <span className="text-zinc-300">—</span>;
  const sign = delta > 0 ? "+" : "";
  if (change === "regression") {
    return (
      <span className="text-rose-700 font-mono text-xs">
        {sign}
        {delta.toFixed(2)}
      </span>
    );
  }
  if (change === "improvement") {
    return (
      <span className="text-emerald-700 font-mono text-xs">
        {sign}
        {delta.toFixed(2)}
      </span>
    );
  }
  return (
    <span className="text-zinc-400 font-mono text-xs">
      {sign}
      {delta.toFixed(2)}
    </span>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "bad" | "warn" | "good" | "neutral";
}) {
  const ring: Record<typeof tone, string> = {
    bad: "border-rose-200 bg-rose-50",
    warn: "border-amber-200 bg-amber-50",
    good: "border-emerald-200 bg-emerald-50",
    neutral: "border-zinc-200 bg-white",
  };
  return (
    <div className={`border rounded-lg p-4 ${ring[tone]}`}>
      <div className="text-xs text-zinc-600 uppercase tracking-wider">
        {label}
      </div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
    </div>
  );
}