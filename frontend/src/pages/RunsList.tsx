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
      <div className="study-heading"><p className="eyebrow">EXPERIMENT NOTEBOOK</p><h1>How do we know a review is good?</h1><p>Compare code reviews across three scoring methods, then inspect the cases where their conclusions differ.</p></div>
      <section className="study-panel" aria-label="Prompt experiment overview">
        <div className="study-caption"><span>01 / PROMPT EXPERIMENTS</span><Link to="/compare">Open comparison →</Link></div>
        <div className="experiment-grid">
          {[...runs].sort((a,b) => a.prompt_version.localeCompare(b.prompt_version)).map(r => (
            <Link className="experiment" key={r.id} to={`/runs/${r.id}`}>
              <div className="experiment-title"><span>{r.prompt_version}</span><h2>{r.prompt_version === "v1" ? "Baseline prompt" : r.prompt_version === "v2" ? "Anti-sycophancy prompt" : "Prompt experiment"}</h2><span aria-hidden="true">→</span></div>
              <p className="experiment-model">{r.model} · {r.dataset_size} cases</p>
              <div className="metric-row"><span>Rule-based pass rate</span><strong>{Math.round((r.summary?.pass_rate ?? 0)*100)}%</strong></div>
              <div className="metric-track"><span style={{width:`${(r.summary?.pass_rate ?? 0)*100}%`}} /></div>
              <div className="metric-row judge-metric"><span>Judge quality score</span><strong>{r.summary?.judge?.mean_quality?.toFixed(1) ?? "—"}<small> / 10</small></strong></div>
              <p className="experiment-link">Inspect scores & disagreements</p>
            </Link>
          ))}
        </div>
        <p className="study-footnote">These are different measures: passing the rules and receiving a high judge score are not equivalent. Results describe this small, recorded benchmark.</p>
      </section>
      <div className="method-strip"><div><b>01</b><strong>Rules</strong><p>Check expected issues, severity, and approval.</p></div><div><b>02</b><strong>LLM judge</strong><p>Llama 3.3 70B scores the quality of each review.</p></div><div><b>03</b><strong>Behavioral probes</strong><p>Classifiers use Qwen2.5-3B activations to flag behavioral signals.</p></div></div>
      <div className="run-register"><h2>Run register</h2><span>{runs.length} recorded runs · newest first</span></div>
      <div className="bg-white border border-zinc-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 text-zinc-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-4 py-3">prompt</th>
              <th className="text-left px-4 py-3">notes</th>
              <th className="text-left px-4 py-3">model</th>
              <th className="text-left px-4 py-3">started</th>
              <th className="text-right px-4 py-3">cases</th>
              <th className="text-right px-4 py-3">Rule pass</th>
              <th className="text-right px-4 py-3">Judge score</th>
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