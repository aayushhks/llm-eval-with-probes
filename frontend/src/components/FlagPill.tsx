const FLAG_LABEL: Record<string, string> = {
  det_fail_judge_good: "deterministic fail · judge approved",
  det_pass_judge_bad: "deterministic pass · judge rejected",
  probe_says_sycophantic_judge_says_fine: "probe: sycophancy · judge: fine",
  probe_says_uncertain_judge_says_fine: "probe: uncertainty · judge: fine",
  probe_says_ungrounded_judge_says_fine: "probe: ungrounded · judge: fine",
  probe_confirms_failure_via_sycophancy: "probe confirms failure (sycophancy)",
  probe_confirms_failure_via_uncertainty: "probe confirms failure (uncertainty)",
};

// Which tone each flag deserves: the probe-vs-judge disagreements are the
// headline story so they get the strongest treatment.
const FLAG_TONE: Record<string, string> = {
  det_fail_judge_good: "bg-rose-50 text-rose-800 border-rose-200",
  det_pass_judge_bad: "bg-amber-50 text-amber-800 border-amber-200",
  probe_says_sycophantic_judge_says_fine:
    "bg-rose-100 text-rose-900 border-rose-300 font-semibold",
  probe_says_uncertain_judge_says_fine:
    "bg-amber-100 text-amber-900 border-amber-300 font-semibold",
  probe_says_ungrounded_judge_says_fine:
    "bg-violet-100 text-violet-900 border-violet-300 font-semibold",
  probe_confirms_failure_via_sycophancy:
    "bg-zinc-50 text-zinc-700 border-zinc-200",
  probe_confirms_failure_via_uncertainty:
    "bg-zinc-50 text-zinc-700 border-zinc-200",
};

export function FlagPill({ flag }: { flag: string }) {
  const label = FLAG_LABEL[flag] || flag;
  const tone =
    FLAG_TONE[flag] || "bg-zinc-50 text-zinc-700 border-zinc-200";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded border text-xs ${tone}`}
    >
      {label}
    </span>
  );
}