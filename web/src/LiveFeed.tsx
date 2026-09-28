import { fmtClock } from "./api";
import type { LiveEvent } from "./api";
import type { WsKind, WsMsg } from "./types";

const KIND_META: Record<WsKind, { badge: string; cls: string }> = {
  pos_event: { badge: "POS", cls: "b-pos" },
  vision_event: { badge: "Vision", cls: "b-vision" },
  anomaly: { badge: "Anomali", cls: "b-anomaly" },
  state_change: { badge: "Durum", cls: "b-state" },
  scene_updated: { badge: "Sahne", cls: "b-state" },
};

function str(d: Record<string, unknown>, key: string): string | null {
  const v = d[key];
  if (typeof v === "string" && v) return v;
  if (typeof v === "number") return String(v);
  return null;
}

function summarize(msg: WsMsg): string {
  const d = msg.data;
  if (msg.kind === "state_change") {
    const actor = str(d, "actor_id") ?? "?";
    const old = str(d, "old") ?? "?";
    const next = str(d, "new") ?? "?";
    return `${actor}: ${old} → ${next}`;
  }
  if (msg.kind === "scene_updated") return "Bölge konfigürasyonu güncellendi";
  if (msg.kind === "anomaly") {
    const title = str(d, "title");
    const sev = str(d, "severity");
    return [title ?? "Anomali", sev ? `ciddiyet: ${sev}` : null]
      .filter(Boolean)
      .join(" · ");
  }
  const type = str(d, "event_type") ?? str(d, "event") ?? str(d, "type") ?? msg.kind;
  const what = str(d, "item_name") ?? str(d, "object_class") ?? str(d, "title");
  const table = str(d, "table_id");
  return [type, what, table ? `masa ${table}` : null].filter(Boolean).join(" · ");
}

export function LiveFeed({ events }: { events: LiveEvent[] }) {
  return (
    <section className="card feed-card">
      <div className="card-head">
        <h2>Canlı Akış</h2>
        <span className="card-hint">son {Math.min(events.length, 50)} olay</span>
      </div>
      {events.length === 0 ? (
        <div className="empty">
          Olay bekleniyor — backend'den WebSocket mesajı gelmedi.
        </div>
      ) : (
        <ul className="feed-list">
          {events.slice(0, 50).map((ev) => {
            const meta = KIND_META[ev.msg.kind] ?? KIND_META.vision_event;
            return (
              <li className="feed-row" key={ev.id}>
                <span className="feed-time">{fmtClock(ev.msg.at_ms)}</span>
                <span className={`badge ${meta.cls}`}>{meta.badge}</span>
                <span className="feed-text">{summarize(ev.msg)}</span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
