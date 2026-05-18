import type { ReactNode } from "react";

type Tone = "neutral" | "good" | "bad" | "warn" | "info";

const TONE_CLASS: Record<Tone, string> = {
  neutral: "bg-zinc-100 text-zinc-700",
  good: "bg-emerald-100 text-emerald-800",
  bad: "bg-rose-100 text-rose-800",
  warn: "bg-amber-100 text-amber-800",
  info: "bg-sky-100 text-sky-800",
};

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${TONE_CLASS[tone]}`}
    >
      {children}
    </span>
  );
}