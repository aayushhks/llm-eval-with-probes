import { useEffect, useState } from "react";
import { getEvidence, type Evidence } from "../components/CaseEvidence";
export default function Validation() {
  const [data, setData] = useState<Evidence>();
  const [error, setError] = useState("");
  useEffect(() => {
    getEvidence()
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);
  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p>Loading validation records…</p>;
  return (
    <div className="validation-page">
      <p className="eyebrow">METHODS & EVIDENCE</p>
      <h1>What has actually been validated?</h1>
      <p className="validation-intro">
        A record of the data, evaluation boundaries, and measurements still
        needed before making stronger claims.
      </p>
      <section>
        <h2>Count cases, not overlapping flags</h2>
        <p>
          {Object.entries(data.unique_probe_disagreements)
            .map(([p, n]) => `${p}: ${n} unique cases`)
            .join(" · ")}{" "}
          where a probe flag disagrees with a high judge score. One case can
          trigger several flags; adding flag totals overcounts reviews. These
          are disagreements requiring review, not independently verified model
          failures.
        </p>
      </section>
      <section>
        <h2>Probe training audit</h2>
        <p>
          The seed examples reuse code diffs. Random example-level splits can
          put the same code in both training and test sets. The new protocol
          holds out an entire diff at a time and refits the classifier on the
          remaining groups.
        </p>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Probe</th>
                <th>Pairs</th>
                <th>Positive labels</th>
                <th>Unique diffs</th>
                <th>Held-out validation</th>
              </tr>
            </thead>
            <tbody>
              {data.probe_audit.map((p) => (
                <tr key={p.name}>
                  <td>{p.name.replace("is_", "")}</td>
                  <td>{p.examples}</td>
                  <td>{p.positive}</td>
                  <td>{p.diff_groups}</td>
                  <td>
                    {p.status === "not_run"
                      ? "Not yet run"
                      : p.status.replaceAll("_", " ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="reading-note">
          No new held-out scores are claimed here. The archived probe scores
          have not been re-trained or replaced. Training-set accuracy and legacy
          random-split accuracy are not evidence of generalization to new code.
        </p>
        {data.probe_audit
          .filter((p) => p.validation)
          .map((p) => (
            <details key={p.name}>
              <summary>{p.name} validation record</summary>
              <pre>{JSON.stringify(p.validation, null, 2)}</pre>
            </details>
          ))}
      </section>
      <section>
        <h2>Thresholds & model boundaries</h2>
        <p>{data.threshold_note}</p>
        <dl className="threshold-list">
          {Object.entries(data.flag_thresholds).map(([k, v]) => (
            <div key={k}>
              <dt>{k.replaceAll("_", " ")}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
        <p>
          The subject model is Llama 3.1 8B. The judge is Llama 3.3 70B. Probe
          features are extracted from a separate Qwen2.5-3B model reading the
          diff and review. They do not expose Llama’s internal state, and their
          scores are not calibrated probabilities of a real failure.
        </p>
      </section>
      <section>
        <h2>Expanded benchmark</h2>
        <p>
          A separate candidate dataset contains{" "}
          {data.candidate_dataset.total_cases} cases: the original 20 plus{" "}
          {data.candidate_dataset.new_cases} new cases across all five
          categories. The new examples are AI-assisted drafts awaiting
          independent review and model execution. They do not change the
          archived scores.
        </p>
      </section>
      <section>
        <h2>Repeated experiments</h2>
        <p>{data.repeated_experiments.reason}</p>
        <p>
          Archived runs:{" "}
          {Object.entries(data.run_counts)
            .map(([k, v]) => `${k}: ${v}`)
            .join(" · ")}
          . Repeatability status:{" "}
          <strong>
            {data.repeated_experiments.status.replaceAll("_", " ")}
          </strong>
          .
        </p>
        {data.repeat_report && (
          <pre>
            {JSON.stringify(
              data.repeat_report.summary ?? {
                status: data.repeat_report.status,
              },
              null,
              2,
            )}
          </pre>
        )}
        <p>
          The repeat runner alternates v1 → v2 and v2 → v1, uses the same
          dataset and model settings, records unique run IDs and dataset hashes,
          and reports paired pass-rate changes. It only reports an interval
          after three completed pairs.
        </p>
        <pre>uv run python ../scripts/run_repeated_eval.py --rounds 3</pre>
        <p>
          This command previews the plan. Real execution requires{" "}
          <code>--execute</code>, a configured database, provider credentials,
          and trained probes (or explicit <code>--no-probes</code>). A replay is
          never counted as a fresh model experiment.
        </p>
      </section>
      <section>
        <h2>Case review workflow</h2>
        <p>
          Open an experiment, expand a disagreement, and inspect its original
          code diff and expected behavior next to the model review and judge
          reasoning. Save your own verdict and explanation, then export the
          annotation as JSON. No independent human adjudication is claimed until
          those assessments are collected.
        </p>
      </section>
    </div>
  );
}
