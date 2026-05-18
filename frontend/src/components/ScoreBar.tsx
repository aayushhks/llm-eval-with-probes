// Small horizontal bar showing 0–1 probability, color-coded by intensity.

type Tone = "syco" | "uncert" | "ungrnd" | "refuse" | "neutral";

const TONE_BG: Record<Tone, string> = {
  syco: "bg-rose-500",
  uncert: "bg-amber-500",
  ungrnd: "bg-violet-500",
  refuse: "bg-sky-500",
  neutral: "bg-zinc-400",
};

export function ScoreBar({
  value,
  tone = "neutral",
  label,
}: {
  value: number | null;
  tone?: Tone;
  label?: string;
}) {
  if (value === null) {
    return (
      <div className="flex items-center gap-2 text-xs text-zinc-300">
        {label && <span className="w-16">{label}</span>}
        <span>—</span>
      </div>
    );
  }
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="flex items-center gap-2 text-xs">
      {label && <span className="w-16 text-zinc-500">{label}</span>}
      <div className="flex-1 bg-zinc-100 rounded h-2 overflow-hidden">
        <div
          className={`h-full ${TONE_BG[tone]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-12 text-right font-mono text-zinc-700">
        {value.toFixed(2)}
      </span>
    </div>
  );
}