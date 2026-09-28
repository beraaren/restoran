import { useEffect, useMemo, useState } from "react";
import { getState, useResource, useWebSocket } from "./api";
import { Admin } from "./Admin";
import { Panel } from "./Panel";
import { ZoneEditor } from "./ZoneEditor";

type TabKey = "panel" | "admin" | "zones";

const TABS: { key: TabKey; label: string }[] = [
  { key: "panel", label: "Panel" },
  { key: "admin", label: "Yönetim" },
  { key: "zones", label: "Bölge Çizimi" },
];

function tabFromHash(): TabKey {
  const h = window.location.hash.replace(/^#/, "");
  return h === "admin" || h === "zones" ? h : "panel";
}

export default function App() {
  const [tab, setTab] = useState<TabKey>(tabFromHash);
  const { status, events } = useWebSocket();
  const stateRes = useResource(getState, 2000);

  useEffect(() => {
    const onHash = () => setTab(tabFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const go = (t: TabKey) => {
    window.location.hash = t;
    setTab(t);
  };

  const sceneVersion = useMemo(
    () => events.reduce((n, e) => (e.msg.kind === "scene_updated" ? n + 1 : n), 0),
    [events],
  );

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className={`live-dot ${status === "open" ? "ok" : "bad"}`} />
          <h1>
            Mutfak İzleme <span>Merkezi</span>
          </h1>
        </div>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={tab === t.key ? "tab active" : "tab"}
              onClick={() => go(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <div className="topbar-right">
          {stateRes.data?.calibrating && (
            <span className="pill pill-amber">Kalibrasyon</span>
          )}
          <span className={`conn-badge ${status}`}>
            {status === "open"
              ? "Canlı bağlantı"
              : status === "connecting"
                ? "Bağlanıyor…"
                : "Bağlantı yok"}
          </span>
        </div>
      </header>

      <main className="content">
        {tab === "panel" && (
          <Panel events={events} state={stateRes.data} stateError={stateRes.error} />
        )}
        {tab === "admin" && <Admin />}
        {tab === "zones" && <ZoneEditor sceneVersion={sceneVersion} />}
      </main>
    </div>
  );
}
