import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type RunListItem } from "../lib/api";
import { Badge } from "../components/Badge";

export default function RunsList() {
  const [runs, setRuns] = useState<RunListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listRuns(50)
      .then(setRuns)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return (
      <div className="text-rose-700 bg-rose-50 border border-rose-200 rounded p-4">
        Couldn't load runs: {error}
      </div>
    );
  }

  if (runs === null) {
    return <div className="text-zinc-500">Loading runs…</div>;
  }

  if (runs.length === 0) {
    return (
      <div className="text-zinc-500">
        No runs yet. Run <code className="bg-zinc-100 px-1 rounded">make eval-v1</code> to create one.
      </div>
    );
  }

  return (
    <div>
      <div className="bg-sky-50 border border-sky-200 rounded-lg p-4 mb-6">
        <div className="text-sm text-zinc-700 leading-relaxed">
          <strong>Three scorers per case</strong> — deterministic rules, an LLM-as-judge (Llama 3.3 70B),
          and probing classifiers trained on Qwen2.5-3B hidden states. Where the three disagree
          is where the interesting failures live. Click a run marked{" "}
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-sky-100 text-sky-800">on</span>
          {" "}in the probes column to see the full disagreement story, or head to{" "}
          <Link to="/compare" className="text-sky-700 underline hover:text-sky-900">compare</Link>
          {" "}to diff two runs.
        </div>
      </div>

      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
        <p className="text-sm text-zinc-500 mt-1">
          {runs.length} run{runs.length === 1 ? "" : "s"}, newest first
        </p>
      </div>

      <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 text-zinc-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-4 py-3">prompt</th>
              <th className="text-left px-4 py-3">notes</th>
              <th className="text-left px-4 py-3">model</th>
              <th className="text-left px-4 py-3">started</th>
              <th className="text-right px-4 py-3">cases</th>
              <th className="text-right px-4 py-3">det pass</th>
              <th className="text-right px-4 py-3">judge mean</th>
              <th className="text-left px-4 py-3">probes</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <RunRow key={r.id} run={r} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RunRow({ run }: { run: RunListItem }) {
  const passRate = run.summary?.pass_rate ?? 0;
  const passed = run.summary?.passed ?? 0;
  const total = run.summary?.total ?? 0;
  const judgeMean = run.summary?.judge?.mean_quality ?? null;
  const probes = run.summary?.probes;
  const hasProbes =
    probes && Object.values(probes).some((p) => p.mean !== null && p.n > 0);

  return (
    <tr className="border-t border-zinc-100 hover:bg-zinc-50">
      <td className="px-4 py-3">
        <Link
          to={`/runs/${run.id}`}
          className="font-medium text-zinc-900 hover:text-sky-700"
        >
          {run.prompt_version}
        </Link>
      </td>
      <td className="px-4 py-3 text-zinc-600 text-xs max-w-xs truncate">
        {run.notes || <span className="text-zinc-300">—</span>}
      </td>
      <td className="px-4 py-3 font-mono text-xs text-zinc-600">
        {run.model}
      </td>
      <td className="px-4 py-3 text-zinc-600">
        {formatTime(run.started_at)}
      </td>
      <td className="px-4 py-3 text-right">{run.dataset_size}</td>
      <td className="px-4 py-3 text-right">
        <Badge tone={passRate >= 0.7 ? "good" : passRate >= 0.4 ? "warn" : "bad"}>
          {passed}/{total} ({Math.round(passRate * 100)}%)
        </Badge>
      </td>
      <td className="px-4 py-3 text-right">
        {judgeMean !== null ? (
          <Badge tone={judgeMean >= 7 ? "good" : judgeMean >= 5 ? "warn" : "bad"}>
            {judgeMean.toFixed(1)}/10
          </Badge>
        ) : (
          <span className="text-zinc-300">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        {hasProbes ? (
          <Badge tone="info">on</Badge>
        ) : (
          <span className="text-zinc-300">—</span>
        )}
      </td>
    </tr>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}