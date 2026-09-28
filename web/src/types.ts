export type Severity = "high" | "medium" | "low";

export interface Anomaly {
  anomaly_id: string;
  kind: string;
  severity: Severity;
  occurred_at_ms: number;
  amount_tl: string | null;
  title: string;
  detail: string;
  table_id: string | null;
  track_id: number | null;
  suppressed: boolean;
}

export interface ActorRec {
  id: string;
  state: string;
  since_ms: number;
}

export type ActorType = "plate" | "table" | "customer" | "chef" | "waiter";

export interface StateResp {
  actors: Record<ActorType, ActorRec[]>;
  counts: { plates_out: number; tickets: number };
  calibrating: boolean;
  zone_to_table: Record<string, string>;
}

export interface Point {
  x: number;
  y: number;
}

export type ZoneKind =
  | "table"
  | "prep"
  | "wash"
  | "pass_out"
  | "entrance"
  | "pos_terminal"
  | "staff_area"
  | "waiting_area";

export interface Zone {
  zone_id: string;
  kind: ZoneKind;
  label: string;
  polygon: Point[];
  pos_table_id: string | null;
  min_dwell_ms: number;
  enabled: boolean;
}

export interface PassLine {
  zone_id: string;
  kind: "pass_out";
  label: string;
  a: Point;
  b: Point;
  min_dwell_ms?: number;
  enabled: boolean;
}

export interface CameraCfg {
  camera_id: string;
  label: string;
  resolution: [number, number];
  fps: number;
  zones: Zone[];
  pass_lines: PassLine[];
}

export interface SceneConfig {
  venue_id: string;
  cameras: CameraCfg[];
}

export type WsKind =
  | "pos_event"
  | "vision_event"
  | "anomaly"
  | "state_change"
  | "scene_updated";

export interface WsMsg {
  kind: WsKind;
  at_ms: number;
  data: Record<string, unknown>;
}

export interface StateChangeData {
  actor_type: ActorType;
  actor_id: string;
  old: string;
  new: string;
  at_ms: number;
  signal?: string;
}

export interface AdminCounters {
  products: number;
  tables: number;
  staff: number;
  suppliers: number;
  invoices_month: number;
}

export type AdminRow = Record<string, string | number | boolean | object | null>;

export interface InvoiceLine {
  item: string;
  qty: number;
  unit: string;
  price: number;
}
