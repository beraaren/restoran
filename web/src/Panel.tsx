import { useEffect, useMemo, useRef, useState } from "react";
import { getAnomalies, getScene, useResource, type LiveEvent } from "./api";
import { ActorStates } from "./ActorStates";
import { AnomalyList } from "./AnomalyList";
import { FloorMap } from "./FloorMap";
import { KpiBar } from "./KpiBar";
import { LiveFeed } from "./LiveFeed";
import { ANOMALY_POLL_MS } from "./config";
import type {
  ActorRec,
  ActorType,
  Anomaly,
  StateChangeData,
  StateResp,
} from "./types";

interface PanelProps {
  events: LiveEvent[];
  state: StateResp | null;
  stateError: boolean;
}

export function Panel({ events, state, stateError }: PanelProps) {
  const anomaliesRes = useResource(getAnomalies, ANOMALY_POLL_MS);
  const sceneRes = useResource(getScene);
  const [wsAnomalies, setWsAnomalies] = useState<Anomaly[]>([]);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const lastSeenRef = useRef(0);

  useEffect(() => {
    const fresh = events.filter((e) => e.id > lastSeenRef.current);
    if (fresh.length === 0) return;
    lastSeenRef.current = Math.max(...fresh.map((e) => e.id));
    for (const ev of [...fresh].sort((a, b) => a.id - b.id)) {
      const m = ev.msg;
      if (m.kind === "state_change") {
        const d = m.data as unknown as StateChangeData;
        if (d.actor_type && d.actor_id && d.new) {
          const key = `${d.actor_type}:${d.actor_id}`;
          setOverrides((prev) => ({ ...prev, [key]: d.new }));
        }
      } else if (m.kind === "anomaly") {
        const a = m.data as unknown as Anomaly;
        if (a?.anomaly_id) {
          setWsAnomalies((prev) =>
            prev.some((x) => x.anomaly_id === a.anomaly_id)
              ? prev
              : [a, ...prev].slice(0, 100),
          );
        }
      } else if (m.kind === "scene_updated") {
        sceneRes.refresh();
      }
    }
  }, [events, sceneRes]);

  const anomalies = useMemo(() => {
    const map = new Map<string, Anomaly>();
    for (const a of wsAnomalies) map.set(a.anomaly_id, a);
    for (const a of anomaliesRes.data ?? [])
      if (!map.has(a.anomaly_id)) map.set(a.anomaly_id, a);
    return [...map.values()].sort((x, y) => y.occurred_at_ms - x.occurred_at_ms);
  }, [wsAnomalies, anomaliesRes.data]);

  const liveState = useMemo<StateResp | null>(() => {
    if (!state) return null;
    const actors = {} as Record<ActorType, ActorRec[]>;
    for (const [type, list] of Object.entries(state.actors)) {
      const t = type as ActorType;
      actors[t] = list.map((a: ActorRec) => {
        const o = overrides[`${t}:${a.id}`];
        return o && o !== a.state ? { ...a, state: o } : a;
      });
    }
    return { ...state, actors };
  }, [state, overrides]);

  const pulse = events[0]?.id ?? 0;

  return (
    <div className="panel-grid">
      <div className="span-12">
        <KpiBar state={liveState} anomalies={anomalies} pulse={pulse} />
        {stateError && (
          <div className="offline-note">
            Backend'e ulaşılamıyor — veriler boş görünüyor, otomatik deneme sürüyor.
          </div>
        )}
      </div>
      <LiveFeed events={events} />
      <AnomalyList anomalies={anomalies} />
      <ActorStates state={liveState} />
      <FloorMap scene={sceneRes.data} state={liveState} />
    </div>
  );
}
