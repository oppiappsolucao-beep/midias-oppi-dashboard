import type { ReactNode } from "react";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  variant?: "" | "metric-card-green" | "metric-card-orange" | "metric-card-blue";
}

export function MetricCard({ title, value, subtitle, variant = "" }: MetricCardProps) {
  return (
    <div className={`metric-card ${variant}`}>
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</div>
      <div className="mt-1 text-2xl font-bold text-oppi-navy">{value}</div>
      {subtitle && <div className="mt-1 text-xs text-slate-500">{subtitle}</div>}
    </div>
  );
}
