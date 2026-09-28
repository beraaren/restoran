import { fmtClock } from "./api";
import type { ActorRec, StateResp } from "./types";

export function stateTone(s: string): string {
  switch (s) {
    case "DOLU":
    case "HAZIRLANDI":
    case "MESAIDE":
      return "teal";
    case "SIPARIS_VAR":
    case "SIPARIS_EDILDI":
    case "SIPARIS_UZERINDE":
      return "amber";
    case "SERVIS_EDILDI":
    case "SERVISTE":
      return "green";
    case "TEMIZLIK_BEKLIYOR":
    case "KIZAKTA":
      return "purple";
    case "KAYIP":
    case "TASAK":
      return "red";
    default:
      return "slate";
  }
}

function ActorRow({ a }: { a: ActorRec }) {
  return (
    <li className="actor-row">
      <span className="actor-id">{a.id}</span>
      <span className={`state-badge tone-${stateTone(a.state)}`}>{a.state}</span>
      <span className="actor-since">{fmtClock(a.since_ms)}</span>
    </li>
  );
}

export function ActorStates({ state }: { state: StateResp | null }) {
  if (!state) {
    return (
      <section className="card actor-card">
        <div className="card-head">
          <h2>Aktör Durumları</h2>
        </div>
        <div className="empty">Durum verisi alınamadı — backend'e bağlanılıyor.</div>
      </section>
    );
  }

  const { table, plate, chef, waiter, customer } = state.actors;
  const staff = [...chef, ...waiter, ...customer];

  return (
    <section className="card actor-card">
      <div className="card-head">
        <h2>Aktör Durumları</h2>
        <span className="card-hint">
          {table.length} masa · {plate.length} tabak · 2 sn polling
        </span>
      </div>
      <div className="actor-cols">
        <div className="actor-col">
          <div className="actor-head">Masalar</div>
          {table.length === 0 ? (
            <div className="empty empty-sm">Masa aktörü yok.</div>
          ) : (
            <ul className="actor-list">
              {table.map((a) => (
                <ActorRow a={a} key={`t-${a.id}`} />
              ))}
            </ul>
          )}
        </div>
        <div className="actor-col">
          <div className="actor-head">Tabaklar</div>
          {plate.length === 0 ? (
            <div className="empty empty-sm">Tabak aktörü yok.</div>
          ) : (
            <ul className="actor-list">
              {plate.map((a) => (
                <ActorRow a={a} key={`p-${a.id}`} />
              ))}
            </ul>
          )}
        </div>
        <div className="actor-col">
          <div className="actor-head">Personel / Müşteri</div>
          {staff.length === 0 ? (
            <div className="empty empty-sm">Kayıt yok.</div>
          ) : (
            <ul className="actor-list">
              {staff.map((a) => (
                <ActorRow a={a} key={`s-${a.id}`} />
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
