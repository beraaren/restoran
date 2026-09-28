import { useEffect, useRef, useState } from "react";
import { API_BASE, WS_RECONNECT_MS, WS_URL } from "./config";
import type {
  AdminCounters,
  AdminRow,
  Anomaly,
  SceneConfig,
  StateResp,
  WsMsg,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const ctrl = new AbortController();
  const timer = window.setTimeout(() => ctrl.abort(), 6000);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      signal: ctrl.signal,
      ...init,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const text = await res.text();
    return (text ? JSON.parse(text) : {}) as T;
  } finally {
    window.clearTimeout(timer);
  }
}

export const getHealth = () =>
  request<{ ok: boolean; uptime_s: number }>("/health");
export const getAnomalies = () => request<Anomaly[]>("/anomalies");
export const getState = () => request<StateResp>("/state");
export const getScene = () => request<SceneConfig>("/scene");
export const putScene = (scene: SceneConfig) =>
  request<unknown>("/scene", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scene),
  });

export const getAdminList = (resource: string) =>
  request<AdminRow[]>(`/admin/${resource}`);
export const getAdminCounters = () =>
  request<AdminCounters>("/admin/summary/counters");
export const postAdmin = (resource: string, fields: Record<string, unknown>) =>
  request<AdminRow>(`/admin/${resource}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
export const deleteAdmin = (resource: string, id: string) =>
  request<unknown>(`/admin/${resource}/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });

export interface FetchResult<T> {
  data: T | null;
  error: boolean;
  refresh: () => void;
}

export function useResource<T>(
  loader: () => Promise<T>,
  pollMs?: number,
): FetchResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState(false);
  const [tick, setTick] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    let alive = true;
    const run = async () => {
      try {
        const d = await loaderRef.current();
        if (alive) {
          setData(d);
          setError(false);
        }
      } catch {
        if (alive) setError(true);
      }
    };
    run();
    if (!pollMs) return () => void (alive = false);
    const t = window.setInterval(run, pollMs);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, [pollMs, tick]);

  return { data, error, refresh: () => setTick((v) => v + 1) };
}

export interface LiveEvent {
  id: number;
  msg: WsMsg;
}

export type WsStatus = "open" | "connecting" | "closed";

export function useWebSocket(): { status: WsStatus; events: LiveEvent[] } {
  const [status, setStatus] = useState<WsStatus>("connecting");
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const seqRef = useRef(0);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer = 0;
    let dead = false;

    const connect = () => {
      if (dead) return;
      setStatus("connecting");
      try {
        ws = new WebSocket(WS_URL);
      } catch {
        setStatus("closed");
        timer = window.setTimeout(connect, WS_RECONNECT_MS);
        return;
      }
      ws.onopen = () => setStatus("open");
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(String(e.data)) as WsMsg;
          seqRef.current += 1;
          const ev: LiveEvent = { id: seqRef.current, msg };
          setEvents((prev) => [ev, ...prev].slice(0, 80));
        } catch {
          /* bozuk kareyi yok say */
        }
      };
      ws.onclose = () => {
        if (dead) return;
        setStatus("closed");
        timer = window.setTimeout(connect, WS_RECONNECT_MS);
      };
      ws.onerror = () => ws?.close();
    };

    connect();
    return () => {
      dead = true;
      window.clearTimeout(timer);
      ws?.close();
    };
  }, []);

  return { status, events };
}

export function fmtClock(ms: number): string {
  const d = new Date(ms);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
