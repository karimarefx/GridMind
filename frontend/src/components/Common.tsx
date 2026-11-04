import type { ReactNode } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  Database,
  FlaskConical,
} from "lucide-react";
export const fmt = (n: number | null | undefined, digits = 0) =>
  n == null
    ? "Unavailable"
    : new Intl.NumberFormat("en-US", {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      }).format(n);
export const utc = (s: string) =>
  new Date(s).toLocaleString("en-GB", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }) + " UTC";
export function Badge({
  kind = "prediction",
  children,
}: {
  kind?: string;
  children?: ReactNode;
}) {
  return (
    <span className={`badge ${kind}`}>
      {kind === "simulated" ? (
        <FlaskConical size={11} />
      ) : (
        <Database size={11} />
      )}{" "}
      {children ??
        (kind === "simulated"
          ? "Simulated demonstration"
          : kind === "observed"
            ? "Observed — ERCOT dataset"
            : kind === "calculated"
              ? "Calculated"
              : "Precomputed model predictions")}
    </span>
  );
}
export function Panel({
  title,
  eyebrow,
  children,
  extra,
  className = "",
}: {
  title?: string;
  eyebrow?: string;
  children: ReactNode;
  extra?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          {eyebrow && <div className="eyebrow">{eyebrow}</div>}
          {title && <h2>{title}</h2>}
        </div>
        {extra}
      </div>
      {children}
    </section>
  );
}
export function Notice({
  title = "Unavailable",
  children,
}: {
  title?: string;
  children: ReactNode;
}) {
  return (
    <div className="notice" role="status">
      <AlertCircle size={19} />
      <div>
        <strong>{title}</strong>
        <p>{children}</p>
      </div>
    </div>
  );
}
export function MetricCard({
  label,
  value,
  unit = "MW",
  kind = "prediction",
  detail,
}: {
  label: string;
  value: string;
  unit?: string;
  kind?: string;
  detail?: string;
}) {
  return (
    <div className={`metric-card ${label.toLowerCase().replaceAll(" ", "-")}`}>
      <div className="metric-label">
        {label}
        <ArrowUpRight size={15} />
      </div>
      <div className="metric-value">
        {value}
        <small>{unit}</small>
      </div>
      <Badge kind={kind} />
      {detail && <p className="muted small">{detail}</p>}
    </div>
  );
}
