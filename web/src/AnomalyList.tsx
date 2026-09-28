import { useState } from "react";
import { fmtClock } from "./api";
import type { Anomaly } from "./types";

const SEV_LABEL: Record<Anomaly["severity"], string> = {
  high: "YÜKSEK",
  medium: "ORTA",
  low: "DÜŞÜK",
};

export function AnomalyList({ anomalies }: { anomalies: Anomaly[] }) {
  const [open, setOpen] = useState<ReadonlySet<string>>(new Set());

  const toggle = (id: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <section className="card anomaly-card">
      <div className="card-head">
        <h2>Anomaliler</h2>
        <span className="card-hint">{anomalies.length} kayıt</span>
      </div>
      {anomalies.length === 0 ? (
        <div className="empty">Henüz anomali tespit edilmedi.</div>
      ) : (
        <ul className="anomaly-list">
          {anomalies.slice(0, 50).map((a) => {
            const expanded = open.has(a.anomaly_id);
            return (
              <li
                key={a.anomaly_id}
                className={`anomaly-item sev-${a.severity}${a.suppressed ? " suppressed" : ""}`}
                onClick={() => toggle(a.anomaly_id)}
              >
                <div className="anomaly-row">
                  <span className="anomaly-time">{fmtClock(a.occurred_at_ms)}</span>
                  <span className="anomaly-title">{a.title}</span>
                  {a.amount_tl && <span className="anomaly-amt">≈ ₺{a.amount_tl}</span>}
                  {a.table_id && <span className="chip">{a.table_id}</span>}
                  {a.suppressed ? (
                    <span className="chip chip-cal">kalibrasyon</span>
                  ) : (
                    <span className={`sev-pill sev-${a.severity}`}>
                      {SEV_LABEL[a.severity]}
                    </span>
                  )}
                </div>
                {expanded && (
                  <div className="anomaly-detail">
                    <div>{a.detail}</div>
                    <div className="anomaly-meta">
                      tip: {a.kind}
                      {a.track_id != null && ` · track #${a.track_id}`}
                      {a.suppressed && " · baskılandı (kalibrasyon modu)"}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
