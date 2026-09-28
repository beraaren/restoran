import { PORTION_PRICE_TL } from "./config";
import type { StateResp } from "./types";

interface KpiBarProps {
  state: StateResp | null;
  anomalies: { suppressed: boolean; kind: string; amount_tl: string | null }[];
  pulse: number;
}

export function KpiBar({ state, anomalies, pulse }: KpiBarProps) {
  const active = anomalies.filter((a) => !a.suppressed);
  let leakTl = 0;
  for (const a of active) {
    const amt = a.amount_tl ? Number.parseFloat(a.amount_tl.replace(",", ".")) : NaN;
    if (Number.isFinite(amt)) leakTl += amt;
    else if (/TICKETSIZ/i.test(a.kind)) leakTl += PORTION_PRICE_TL;
  }

  const cards = [
    {
      label: "Mutfaktan Çıkan Ürün",
      value: state ? String(state.counts.plates_out) : "—",
      sub: "pass üzerinden geçen tabak",
    },
    {
      label: "Fire Edilen Sipariş",
      value: state ? String(state.counts.tickets) : "—",
      sub: "POS ticket sayısı",
    },
    {
      label: "Tespit Edilen Kayıp",
      value: String(active.length),
      sub: "baskılanmamış anomali",
    },
    {
      label: "Kaçak ₺ Tahmini",
      value: `₺${Math.round(leakTl).toLocaleString("tr-TR")}`,
      sub: `ticketsız için ₺${PORTION_PRICE_TL}/porsiyon`,
    },
  ];

  return (
    <div className="kpi-bar">
      {cards.map((c) => (
        <div className="card kpi-card" key={c.label}>
          <div className="kpi-label">{c.label}</div>
          <div className="kpi-value" key={`${c.label}:${pulse}`}>
            {c.value}
          </div>
          <div className="kpi-sub">{c.sub}</div>
        </div>
      ))}
    </div>
  );
}
