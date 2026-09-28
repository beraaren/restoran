import { useCallback, useEffect, useRef, useState } from "react";
import type { PointerEvent as RPointerEvent } from "react";
import { getScene, putScene } from "./api";
import type {
  CameraCfg,
  PassLine,
  Point,
  SceneConfig,
  Zone,
  ZoneKind,
} from "./types";

const KIND_OPTIONS: { kind: ZoneKind; label: string }[] = [
  { kind: "table", label: "Masa" },
  { kind: "prep", label: "Hazırlık" },
  { kind: "wash", label: "Yıkanma" },
  { kind: "pass_out", label: "Geçiş Çizgisi" },
  { kind: "entrance", label: "Giriş" },
  { kind: "pos_terminal", label: "POS Terminali" },
  { kind: "staff_area", label: "Personel Alanı" },
  { kind: "waiting_area", label: "Bekleme Alanı" },
];

const KIND_LABEL: Record<ZoneKind, string> = Object.fromEntries(
  KIND_OPTIONS.map((k) => [k.kind, k.label]),
) as Record<ZoneKind, string>;

const KIND_COLORS: Record<ZoneKind, string> = {
  table: "#0d9488",
  prep: "#2563eb",
  wash: "#0284c7",
  pass_out: "#dc2626",
  entrance: "#7c3aed",
  pos_terminal: "#db2777",
  staff_area: "#d97706",
  waiting_area: "#64748b",
};

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const dist = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y);

function centroid(pts: Point[]): Point {
  const n = Math.max(pts.length, 1);
  return {
    x: pts.reduce((s, p) => s + p.x, 0) / n,
    y: pts.reduce((s, p) => s + p.y, 0) / n,
  };
}

function defaultScene(): SceneConfig {
  return {
    venue_id: "demo",
    cameras: [
      {
        camera_id: "cam0",
        label: "Kamera 1",
        resolution: [1280, 720],
        fps: 25,
        zones: [],
        pass_lines: [],
      },
    ],
  };
}

function nextId(kind: ZoneKind, cam: CameraCfg): string {
  const taken = new Set([
    ...cam.zones.map((z) => z.zone_id),
    ...cam.pass_lines.map((l) => l.zone_id),
  ]);
  let n = 1;
  while (taken.has(`${kind}-${n}`)) n += 1;
  return `${kind}-${n}`;
}

interface DragTarget {
  id: string;
  index: number;
  isLine: boolean;
}

interface ZoneEditorProps {
  sceneVersion: number;
}

export function ZoneEditor({ sceneVersion }: ZoneEditorProps) {
  const [scene, setScene] = useState<SceneConfig | null>(null);
  const [loadErr, setLoadErr] = useState(false);
  const [tool, setTool] = useState<ZoneKind>("table");
  const [drawing, setDrawing] = useState(false);
  const [draft, setDraft] = useState<Point[]>([]);
  const [cursor, setCursor] = useState<Point | null>(null);
  const [selId, setSelId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; kind: "ok" | "err" } | null>(
    null,
  );
  const svgRef = useRef<SVGSVGElement | null>(null);
  const dragRef = useRef<DragTarget | null>(null);
  const loadedRevRef = useRef(0);
  const versionRef = useRef(sceneVersion);
  versionRef.current = sceneVersion;

  const showToast = (text: string, kind: "ok" | "err" = "ok") =>
    setToast({ text, kind });

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 2600);
    return () => window.clearTimeout(t);
  }, [toast]);

  const load = useCallback(async (quiet = false) => {
    try {
      const s = await getScene();
      if (!s.cameras || s.cameras.length === 0) throw new Error("boş sahne");
      setScene(s);
      setLoadErr(false);
      loadedRevRef.current = versionRef.current;
      if (!quiet) showToast("Sahne backend'den yüklendi");
    } catch {
      setLoadErr(true);
      if (!quiet) showToast("Sahne yüklenemedi (backend kapalı?)", "err");
    }
  }, []);

  useEffect(() => {
    void load(true);
  }, [load]);

  useEffect(() => {
    if (sceneVersion > 0 && sceneVersion !== loadedRevRef.current) void load(true);
  }, [sceneVersion, load]);

  const cam = scene?.cameras[0] ?? null;

  const mutateCam = useCallback((fn: (c: CameraCfg) => CameraCfg) => {
    setScene((prev) =>
      prev
        ? { ...prev, cameras: prev.cameras.map((c, i) => (i === 0 ? fn(c) : c)) }
        : prev,
    );
  }, []);

  const toNorm = (e: { clientX: number; clientY: number }): Point => {
    const r = svgRef.current!.getBoundingClientRect();
    return {
      x: clamp01((e.clientX - r.left) / r.width),
      y: clamp01((e.clientY - r.top) / r.height),
    };
  };

  const cancelDrawing = () => {
    setDrawing(false);
    setDraft([]);
    setCursor(null);
  };

  const commitPolygon = useCallback(
    (points: Point[]) => {
      if (!cam) return;
      const clean: Point[] = [];
      for (const p of points)
        if (clean.length === 0 || dist(p, clean[clean.length - 1]) > 0.004)
          clean.push(p);
      if (clean.length < 3) {
        showToast("Poligon için en az 3 nokta gerekli", "err");
        cancelDrawing();
        return;
      }
      const id = nextId(tool, cam);
      const n = cam.zones.filter((z) => z.kind === tool).length + 1;
      const zone: Zone = {
        zone_id: id,
        kind: tool,
        label: `${KIND_LABEL[tool]} ${n}`,
        polygon: clean,
        pos_table_id: tool === "table" ? `M${n}` : null,
        min_dwell_ms: 400,
        enabled: true,
      };
      mutateCam((c) => ({ ...c, zones: [...c.zones, zone] }));
      setSelId(id);
      cancelDrawing();
      showToast(`${zone.label} oluşturuldu — henüz kaydedilmedi`);
    },
    [cam, tool, mutateCam],
  );

  useEffect(() => {
    const h = (e: globalThis.KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
      if (e.key === "Escape") cancelDrawing();
      if (e.key === "Enter" && drawing && tool !== "pass_out") {
        e.preventDefault();
        commitPolygon(draft);
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [drawing, draft, tool, commitPolygon]);

  const onCanvasDown = (e: RPointerEvent) => {
    if (e.button !== 0 || !cam) return;
    const p = toNorm(e);
    if (!drawing) {
      setDraft([p]);
      setDrawing(true);
      return;
    }
    if (tool === "pass_out") {
      if (draft.length === 1) {
        if (dist(draft[0], p) > 0.01) {
          const a = draft[0];
          const id = nextId("pass_out", cam);
          const line: PassLine = {
            zone_id: id,
            kind: "pass_out",
            label: `Geçiş ${id.split("-").pop()}`,
            a,
            b: p,
            min_dwell_ms: 0,
            enabled: true,
          };
          mutateCam((c) => ({ ...c, pass_lines: [...c.pass_lines, line] }));
          setSelId(id);
        }
        cancelDrawing();
      }
      return;
    }
    if (draft.length >= 3 && dist(p, draft[0]) < 0.03) {
      commitPolygon([...draft, draft[0]]);
      return;
    }
    setDraft((d) => [...d, p]);
  };

  const onSvgMove = (e: RPointerEvent) => {
    const p = toNorm(e);
    if (dragRef.current) {
      const d = dragRef.current;
      mutateCam((c) => {
        if (d.isLine) {
          return {
            ...c,
            pass_lines: c.pass_lines.map((l) =>
              l.zone_id === d.id
                ? { ...l, [d.index === 0 ? "a" : "b"]: p }
                : l,
            ),
          };
        }
        return {
          ...c,
          zones: c.zones.map((z) =>
            z.zone_id === d.id
              ? { ...z, polygon: z.polygon.map((pt, i) => (i === d.index ? p : pt)) }
              : z,
          ),
        };
      });
      return;
    }
    if (drawing) setCursor(p);
  };

  const onSvgUp = () => {
    dragRef.current = null;
  };

  const startVertexDrag = (
    e: RPointerEvent,
    id: string,
    index: number,
    isLine: boolean,
  ) => {
    e.stopPropagation();
    dragRef.current = { id, index, isLine };
    (e.target as Element).setPointerCapture(e.pointerId);
  };

  const deleteSelected = () => {
    if (!selId || !cam) return;
    mutateCam((c) => ({
      ...c,
      zones: c.zones.filter((z) => z.zone_id !== selId),
      pass_lines: c.pass_lines.filter((l) => l.zone_id !== selId),
    }));
    setSelId(null);
  };

  const patchZone = (patch: Partial<Zone>) =>
    selId &&
    mutateCam((c) => ({
      ...c,
      zones: c.zones.map((z) => (z.zone_id === selId ? { ...z, ...patch } : z)),
    }));

  const patchLine = (patch: Partial<PassLine>) =>
    selId &&
    mutateCam((c) => ({
      ...c,
      pass_lines: c.pass_lines.map((l) =>
        l.zone_id === selId ? { ...l, ...patch } : l,
      ),
    }));

  const save = async () => {
    if (!scene) return;
    try {
      await putScene(scene);
      showToast("Sahne backend'e kaydedildi ✓");
    } catch {
      showToast("Kaydetme başarısız — backend kapalı olabilir", "err");
    }
  };

  const downloadJson = () => {
    if (!scene) return;
    const blob = new Blob([JSON.stringify(scene, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "scene.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const selZone = cam?.zones.find((z) => z.zone_id === selId) ?? null;
  const selLine = cam?.pass_lines.find((l) => l.zone_id === selId) ?? null;

  if (!scene) {
    return (
      <div className="card ze-offline">
        <h2>Sahne yüklenemedi</h2>
        <p>
          Backend'e ulaşılamıyor. Sunucu ayakta olduğunda "Aç" ile mevcut config'i
          yükleyebilir ya da boş bir sahneyle başlayabilirsiniz.
        </p>
        <div className="ze-actions">
          <button className="btn" onClick={() => void load()}>
            Tekrar Dene
          </button>
          <button
            className="btn btn-ghost"
            onClick={() => {
              setScene(defaultScene());
              setLoadErr(false);
            }}
          >
            Boş Sahne Oluştur
          </button>
        </div>
        {loadErr && <div className="hint-danger">Bağlantı hatası: GET /scene</div>}
      </div>
    );
  }

  return (
    <div className="ze-wrap">
      <aside className="ze-palette">
        <div className="card ze-card">
          <div className="card-head">
            <h2>Bölge Tipi</h2>
          </div>
          <div className="kind-grid">
            {KIND_OPTIONS.map((k) => (
              <button
                key={k.kind}
                className={tool === k.kind ? "kind-btn active" : "kind-btn"}
                onClick={() => {
                  setTool(k.kind);
                  cancelDrawing();
                }}
              >
                <span className="kind-dot" style={{ background: KIND_COLORS[k.kind] }} />
                {k.label}
              </button>
            ))}
          </div>
          <div className="hint">
            {drawing
              ? tool === "pass_out"
                ? `İkinci noktayı tıklayın (${draft.length}/2)`
                : "Tıkla-tıkla köşe ekle · Enter/başlangıca tık bitsin · ESC iptal"
              : "Çizmek için bir tip seçip zemine tıklamaya başlayın."}
          </div>
        </div>

        <div className="card ze-card ze-list-card">
          <div className="card-head">
            <h2>Bölgeler</h2>
            <span className="card-hint">
              {(cam?.zones.length ?? 0) + (cam?.pass_lines.length ?? 0)} adet
            </span>
          </div>
          <ul className="ze-list">
            {cam?.zones.map((z) => (
              <li key={z.zone_id}>
                <button
                  className={selId === z.zone_id ? "ze-item active" : "ze-item"}
                  onClick={() => setSelId(z.zone_id)}
                >
                  <span className="kind-dot" style={{ background: KIND_COLORS[z.kind] }} />
                  <span className="ze-item-label">{z.label}</span>
                  {z.pos_table_id && <span className="chip">{z.pos_table_id}</span>}
                  {!z.enabled && <span className="chip chip-cal">kapalı</span>}
                </button>
              </li>
            ))}
            {cam?.pass_lines.map((l) => (
              <li key={l.zone_id}>
                <button
                  className={selId === l.zone_id ? "ze-item active" : "ze-item"}
                  onClick={() => setSelId(l.zone_id)}
                >
                  <span className="kind-dot" style={{ background: KIND_COLORS.pass_out }} />
                  <span className="ze-item-label">{l.label}</span>
                </button>
              </li>
            ))}
          </ul>

          {selZone && (
            <div className="ze-edit">
              <label>
                İsim
                <input
                  value={selZone.label}
                  onChange={(e) => patchZone({ label: e.target.value })}
                />
              </label>
              {selZone.kind === "table" && (
                <label>
                  POS Masa ID
                  <input
                    value={selZone.pos_table_id ?? ""}
                    placeholder="M1"
                    onChange={(e) =>
                      patchZone({ pos_table_id: e.target.value || null })
                    }
                  />
                </label>
              )}
              <label>
                Min. Kalma (ms)
                <input
                  type="number"
                  min={0}
                  value={selZone.min_dwell_ms}
                  onChange={(e) =>
                    patchZone({ min_dwell_ms: Number(e.target.value) || 0 })
                  }
                />
              </label>
              <label className="ze-check">
                <input
                  type="checkbox"
                  checked={selZone.enabled}
                  onChange={(e) => patchZone({ enabled: e.target.checked })}
                />
                Etkin
              </label>
              <button className="btn btn-danger" onClick={deleteSelected}>
                Bölgeyi Sil
              </button>
            </div>
          )}
          {selLine && (
            <div className="ze-edit">
              <label>
                İsim
                <input
                  value={selLine.label}
                  onChange={(e) => patchLine({ label: e.target.value })}
                />
              </label>
              <label className="ze-check">
                <input
                  type="checkbox"
                  checked={selLine.enabled}
                  onChange={(e) => patchLine({ enabled: e.target.checked })}
                />
                Etkin
              </label>
              <button className="btn btn-danger" onClick={deleteSelected}>
                Çizgiyi Sil
              </button>
            </div>
          )}
        </div>
      </aside>

      <section className="ze-main">
        <div className="ze-toolbar">
          <div className="ze-actions">
            <button className="btn" onClick={() => void load()}>
              Aç (GET /scene)
            </button>
            <button className="btn btn-primary" onClick={() => void save()}>
              Kaydet (PUT /scene)
            </button>
            <button className="btn btn-ghost" onClick={downloadJson}>
              JSON İndir
            </button>
            {drawing && (
              <button className="btn btn-ghost" onClick={cancelDrawing}>
                Çizimi İptal (ESC)
              </button>
            )}
          </div>
          <span className="card-hint">
            {scene.venue_id} · {cam ? `${cam.resolution[0]}×${cam.resolution[1]}` : ""} ·{" "}
            normalize koordinat 0..1
          </span>
        </div>

        {cam && (
          <svg
            ref={svgRef}
            className="ze-svg"
            viewBox={`0 0 ${cam.resolution[0]} ${cam.resolution[1]}`}
            onPointerDown={onCanvasDown}
            onPointerMove={onSvgMove}
            onPointerUp={onSvgUp}
            onDoubleClick={() => tool !== "pass_out" && drawing && commitPolygon(draft)}
          >
            <defs>
              <pattern
                id="ze-grid"
                width={cam.resolution[0] / 20}
                height={cam.resolution[1] / 12}
                patternUnits="userSpaceOnUse"
              >
                <path
                  d={`M ${cam.resolution[0] / 20} 0 L 0 0 0 ${cam.resolution[1] / 12}`}
                  fill="none"
                  stroke="#e7eaf3"
                  strokeWidth="1"
                />
              </pattern>
              <marker
                id="ze-arrow"
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
            <rect width="100%" height="100%" fill="#fdfdff" />
            <rect width="100%" height="100%" fill="url(#ze-grid)" />
            <text
              x="50%"
              y="8%"
              textAnchor="middle"
              className="ze-canvas-note"
              fontSize={cam.resolution[0] / 48}
            >
              Kamera görüntüsü üzerine çiz — zemine tıklayarak poligon oluştur
            </text>

            {cam.zones.map((z) => {
              const color = KIND_COLORS[z.kind];
              const c = centroid(z.polygon);
              return (
                <g key={z.zone_id}>
                  <polygon
                    points={z.polygon
                      .map((p) => `${p.x * cam.resolution[0]},${p.y * cam.resolution[1]}`)
                      .join(" ")}
                    fill={`${color}22`}
                    stroke={color}
                    strokeWidth={selId === z.zone_id ? 3 : 1.6}
                    strokeDasharray={z.enabled ? undefined : "6 6"}
                    pointerEvents="none"
                  />
                  <text
                    x={c.x * cam.resolution[0]}
                    y={c.y * cam.resolution[1]}
                    textAnchor="middle"
                    className="ze-zone-label"
                    fontSize={cam.resolution[0] / 80}
                    fill={color}
                  >
                    {z.label}
                  </text>
                  {selId === z.zone_id &&
                    z.polygon.map((p, i) => (
                      <circle
                        key={i}
                        cx={p.x * cam.resolution[0]}
                        cy={p.y * cam.resolution[1]}
                        r={7}
                        className="ze-vertex"
                        onPointerDown={(e) =>
                          startVertexDrag(e, z.zone_id, i, false)
                        }
                      />
                    ))}
                </g>
              );
            })}

            {cam.pass_lines.map((l) => (
              <g key={l.zone_id}>
                <line
                  x1={l.a.x * cam.resolution[0]}
                  y1={l.a.y * cam.resolution[1]}
                  x2={l.b.x * cam.resolution[0]}
                  y2={l.b.y * cam.resolution[1]}
                  stroke="#dc2626"
                  strokeWidth={selId === l.zone_id ? 4 : 2.5}
                  strokeDasharray="10 8"
                  markerEnd="url(#ze-arrow)"
                  pointerEvents="none"
                />
                {selId === l.zone_id &&
                  [l.a, l.b].map((p, i) => (
                    <circle
                      key={i}
                      cx={p.x * cam.resolution[0]}
                      cy={p.y * cam.resolution[1]}
                      r={7}
                      className="ze-vertex"
                      onPointerDown={(e) =>
                        startVertexDrag(e, l.zone_id, i, true)
                      }
                    />
                  ))}
              </g>
            ))}

            {drawing && (
              <g pointerEvents="none">
                {draft.length > 0 && (
                  <polyline
                    points={[...draft, ...(cursor ? [cursor] : [])]
                      .map((p) => `${p.x * cam.resolution[0]},${p.y * cam.resolution[1]}`)
                      .join(" ")}
                    fill="none"
                    stroke="#0d9488"
                    strokeWidth="2"
                    strokeDasharray="7 5"
                  />
                )}
                {draft.map((p, i) => (
                  <circle
                    key={i}
                    cx={p.x * cam.resolution[0]}
                    cy={p.y * cam.resolution[1]}
                    r={i === 0 ? 7 : 5}
                    fill={i === 0 ? "#0d9488" : "#ffffff"}
                    stroke="#0d9488"
                    strokeWidth="2"
                  />
                ))}
              </g>
            )}
          </svg>
        )}
      </section>

      {toast && (
        <div className={`toast toast-${toast.kind}`}>{toast.text}</div>
      )}
    </div>
  );
}
