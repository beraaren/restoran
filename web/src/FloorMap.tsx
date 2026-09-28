import type { CameraCfg, Point, SceneConfig, StateResp } from "./types";

export const TABLE_COLORS: Record<string, string> = {
  BOS: "#94a3b8",
  DOLU: "#0d9488",
  SIPARIS_VAR: "#d97706",
  SERVIS_EDILDI: "#16a34a",
  TEMIZLIK_BEKLIYOR: "#7c3aed",
};

function centroid(pts: Point[]): Point {
  const n = Math.max(pts.length, 1);
  return {
    x: pts.reduce((s, p) => s + p.x, 0) / n,
    y: pts.reduce((s, p) => s + p.y, 0) / n,
  };
}

const LEGEND: [string, string][] = [
  ["BOS", "slate"],
  ["DOLU", "teal"],
  ["SIPARIS_VAR", "amber"],
  ["SERVIS_EDILDI", "green"],
  ["TEMIZLIK_BEKLIYOR", "purple"],
];

export function FloorMap({
  scene,
  state,
}: {
  scene: SceneConfig | null;
  state: StateResp | null;
}) {
  const cam: CameraCfg | null = scene?.cameras[0] ?? null;

  return (
    <section className="card map-card">
      <div className="card-head">
        <h2>Masa Haritası</h2>
        <div className="map-legend">
          {LEGEND.map(([name, tone]) => (
            <span key={name} className="legend-item">
              <span
                className="legend-dot"
                style={{ background: TABLE_COLORS[name] ?? "#94a3b8" }}
              />
              <span className={`legend-text tone-${tone}`}>{name}</span>
            </span>
          ))}
          <span className="legend-item">
            <span className="legend-line" />
            <span className="legend-text tone-red">Geçiş (pass)</span>
          </span>
        </div>
      </div>
      {!cam ? (
        <div className="empty">
          Sahne config'i yüklenemedi — backend kapalı olabilir.
        </div>
      ) : (
        <FloorSvg cam={cam} state={state} />
      )}
    </section>
  );
}

function FloorSvg({ cam, state }: { cam: CameraCfg; state: StateResp | null }) {
  const [W, H] = cam.resolution;
  const fontSize = Math.max(14, Math.round(W / 72));

  const tableState = (zoneId: string): string => {
    const tid = state?.zone_to_table[zoneId];
    if (!tid || !state) return "BOS";
    return state.actors.table.find((t) => t.id === tid)?.state ?? "BOS";
  };

  return (
    <svg
      className="floor-svg"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <pattern id="fmap-grid" width={W / 16} height={H / 9} patternUnits="userSpaceOnUse">
          <path
            d={`M ${W / 16} 0 L 0 0 0 ${H / 9}`}
            fill="none"
            stroke="#e7eaf3"
            strokeWidth="1"
          />
        </pattern>
        <marker
          id="fmap-arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#dc2626" />
        </marker>
      </defs>
      <rect width={W} height={H} fill="#fdfdff" />
      <rect width={W} height={H} fill="url(#fmap-grid)" />

      {cam.zones
        .filter((z) => z.kind !== "table")
        .map((z) => (
          <g key={z.zone_id}>
            <polygon
              points={z.polygon.map((p) => `${p.x * W},${p.y * H}`).join(" ")}
              className="map-other-zone"
            />
            <text
              x={centroid(z.polygon).x * W}
              y={centroid(z.polygon).y * H}
              className="map-other-label"
              fontSize={fontSize - 3}
            >
              {z.label}
            </text>
          </g>
        ))}

      {cam.zones
        .filter((z) => z.kind === "table")
        .map((z) => {
          const st = tableState(z.zone_id);
          const color = TABLE_COLORS[st] ?? "#94a3b8";
          const c = centroid(z.polygon);
          return (
            <g key={z.zone_id}>
              <polygon
                points={z.polygon.map((p) => `${p.x * W},${p.y * H}`).join(" ")}
                fill={`${color}26`}
                stroke={color}
                strokeWidth="2.5"
                className="map-table"
              />
              <text x={c.x * W} y={c.y * H - 6} className="map-label" fontSize={fontSize}>
                {z.label}
              </text>
              <text
                x={c.x * W}
                y={c.y * H + fontSize - 4}
                className="map-sublabel"
                fontSize={fontSize - 4}
                fill={color}
              >
                {z.pos_table_id ?? "—"} · {st}
              </text>
            </g>
          );
        })}

      {cam.pass_lines.map((l) => (
        <g key={l.zone_id}>
          <line
            x1={l.a.x * W}
            y1={l.a.y * H}
            x2={l.b.x * W}
            y2={l.b.y * H}
            stroke="#dc2626"
            strokeWidth="3"
            strokeDasharray="10 8"
            markerEnd="url(#fmap-arrow)"
          />
          <text
            x={(l.a.x + l.b.x) / 2 * W + 12}
            y={(l.a.y + l.b.y) / 2 * H}
            className="map-pass-label"
            fontSize={fontSize - 4}
          >
            {l.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
