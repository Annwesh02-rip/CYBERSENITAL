import type { ReactNode } from 'react';

export default function MetricCard({ label, value, detail, icon }: {
  label: string; value: string | number; detail: string; icon: ReactNode;
}) {
  return <section className="metric-card"><div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div><div className="metric-value">{value}</div><p>{detail}</p></section>;
}
