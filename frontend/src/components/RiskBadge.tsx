import { clsx } from "clsx";

const styles = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high: "bg-orange-100 text-orange-700 border-orange-200",
  medium: "bg-amber-100 text-amber-700 border-amber-200",
  low: "bg-green-100 text-green-700 border-green-200",
};

export function RiskBadge({ level }: { level: string }) {
  const s = styles[level as keyof typeof styles] ?? styles.low;
  return (
    <span className={clsx("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide", s)}>
      {level}
    </span>
  );
}
