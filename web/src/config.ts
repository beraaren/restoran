export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/+$/, "") ??
  "http://localhost:8100";

export const WS_URL: string = API_BASE.replace(/^http/, "ws") + "/ws";

export const STATE_POLL_MS = 2000;
export const ANOMALY_POLL_MS = 10000;
export const WS_RECONNECT_MS = 2000;

export const PORTION_PRICE_TL = 150;
