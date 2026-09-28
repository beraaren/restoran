import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  deleteAdmin,
  getAdminCounters,
  getAdminList,
  getScene,
  postAdmin,
  useResource,
} from "./api";
import type { AdminRow } from "./types";

type FieldDef = {
  key: string;
  label: string;
  type: "text" | "number" | "select" | "checkbox" | "date" | "time";
  options?: [string, string][];
  pk?: boolean;
  default?: string | number | boolean;
  defaultToday?: boolean;
  hideInTable?: boolean;
};

type ResourceDef = {
  resource: string;
  title: string;
  pk: string;
  manualPk?: boolean;
  fields: FieldDef[];
};

const CATS: [string, string][] = [
  ["ana", "Ana Yemek"],
  ["yan", "Yan Ürün"],
  ["icecek", "İçecek"],
  ["tatli", "Tatlı"],
  ["other", "Diğer"],
];

const ROLES: [string, string][] = [
  ["aşçı", "Aşçı"],
  ["garson", "Garson"],
  ["kasiyer", "Kasiyer"],
  ["müdür", "Müdür"],
];

const RESOURCES: ResourceDef[] = [
  {
    resource: "products",
    title: "Ürünler",
    pk: "item_id",
    fields: [
      { key: "item_id", label: "Ürün Kodu", type: "text", pk: true },
      { key: "name", label: "Ad", type: "text" },
      { key: "category", label: "Kategori", type: "select", options: CATS, default: "ana" },
      { key: "price_tl", label: "Fiyat (₺)", type: "number" },
      { key: "cost_tl", label: "Maliyet (₺)", type: "number" },
      { key: "unit", label: "Birim", type: "text", default: "porsiyon" },
      { key: "active", label: "Aktif", type: "checkbox", default: true },
    ],
  },
  {
    resource: "tables",
    title: "Masalar",
    pk: "table_id",
    manualPk: true,
    fields: [
      { key: "table_id", label: "Masa ID", type: "text", pk: true },
      { key: "label", label: "Etiket", type: "text" },
      { key: "seats", label: "Kişi Sayısı", type: "number", default: 4 },
      { key: "zone_id", label: "Bölge", type: "text" },
      { key: "active", label: "Aktif", type: "checkbox", default: true },
    ],
  },
  {
    resource: "staff",
    title: "Personel",
    pk: "staff_id",
    fields: [
      { key: "staff_id", label: "Personel ID", type: "text", pk: true },
      { key: "name", label: "Ad Soyad", type: "text" },
      { key: "role", label: "Rol", type: "select", options: ROLES, default: "garson" },
      { key: "pin", label: "PIN", type: "text" },
      { key: "active", label: "Aktif", type: "checkbox", default: true },
    ],
  },
  {
    resource: "shifts",
    title: "Vardiyalar",
    pk: "shift_id",
    fields: [
      { key: "shift_id", label: "Vardiya ID", type: "text", pk: true },
      { key: "staff_id", label: "Personel ID", type: "text" },
      { key: "day", label: "Gün", type: "date", defaultToday: true },
      { key: "start", label: "Başlangıç", type: "time" },
      { key: "end", label: "Bitiş", type: "time" },
    ],
  },
  {
    resource: "suppliers",
    title: "Tedarikçiler",
    pk: "supplier_id",
    fields: [
      { key: "supplier_id", label: "Tedarikçi ID", type: "text", pk: true },
      { key: "name", label: "Ad", type: "text" },
      { key: "contact", label: "İletişim", type: "text" },
      { key: "active", label: "Aktif", type: "checkbox", default: true },
    ],
  },
  {
    resource: "invoices",
    title: "Faturalar",
    pk: "invoice_id",
    fields: [
      { key: "invoice_id", label: "Fatura No", type: "text", pk: true },
      { key: "supplier_id", label: "Tedarikçi ID", type: "text" },
      { key: "day", label: "Gün", type: "date", defaultToday: true },
      { key: "total_tl", label: "Tutar (₺)", type: "number" },
      { key: "lines", label: "Kalemler (JSON dizi)", type: "text", hideInTable: true },
    ],
  },
  {
    resource: "stock",
    title: "Stok Sayımı",
    pk: "count_id",
    fields: [
      { key: "count_id", label: "Sayım ID", type: "text", pk: true },
      { key: "day", label: "Gün", type: "date", defaultToday: true },
      { key: "item", label: "Ürün", type: "text" },
      { key: "qty", label: "Sayılan", type: "number" },
      { key: "unit", label: "Birim", type: "text" },
      { key: "expected_qty", label: "Beklenen", type: "number" },
      { key: "counted_by", label: "Sayan", type: "text" },
    ],
  },
];

function fmtTl(v: unknown): string {
  const n = Number(v);
  return Number.isFinite(n)
    ? `₺${n.toLocaleString("tr-TR", { maximumFractionDigits: 2 })}`
    : "—";
}

function safeJson(s: string): unknown {
  try {
    return JSON.parse(s);
  } catch {
    return null;
  }
}

function todayStr(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function cellValue(row: AdminRow, key: string, zoneLabels: Record<string, string>): string {
  const v = row[key];
  if (v === null || v === undefined || v === "") return "—";
  if (key === "price_tl" || key === "cost_tl" || key === "total_tl") return fmtTl(v);
  if (key === "lines") {
    const lines = typeof v === "string" ? safeJson(v) : v;
    return Array.isArray(lines) ? `${lines.length} kalem` : "—";
  }
  if (key === "zone_id") {
    const zid = String(v);
    const lab = zoneLabels[zid];
    return lab ? `${zid} · ${lab}` : zid;
  }
  if (typeof v === "boolean") return v ? "Evet" : "Hayır";
  return String(v);
}

function stockMismatch(row: AdminRow): boolean {
  const a = Number(row.qty);
  const b = Number(row.expected_qty);
  return Number.isFinite(a) && Number.isFinite(b) && a !== b;
}

type Toast = { text: string; kind: "ok" | "err" } | null;

export function Admin() {
  const [active, setActive] = useState("products");
  const [toast, setToast] = useState<Toast>(null);
  const counters = useResource(getAdminCounters, 15000);
  const sceneRes = useResource(getScene);

  const zoneLabels = useMemo(() => {
    const map: Record<string, string> = {};
    for (const cam of sceneRes.data?.cameras ?? []) {
      for (const z of cam.zones) map[z.zone_id] = z.label;
      for (const l of cam.pass_lines) map[l.zone_id] = l.label;
    }
    return map;
  }, [sceneRes.data]);

  const def = useMemo(
    () => RESOURCES.find((r) => r.resource === active) ?? RESOURCES[0],
    [active],
  );

  const notify = (text: string, kind: "ok" | "err" = "ok") => {
    setToast({ text, kind });
    window.setTimeout(() => setToast(null), 2600);
  };

  return (
    <div className="admin-wrap">
      <aside className="admin-side">
        <div className="card admin-counters">
          <div className="card-head">
            <h2>Özet</h2>
          </div>
          {counters.error && !counters.data ? (
            <div className="empty empty-sm">Bağlantı yok</div>
          ) : (
            <ul className="counter-list">
              <li><span>Ürün</span><b>{counters.data?.products ?? "…"}</b></li>
              <li><span>Masa</span><b>{counters.data?.tables ?? "…"}</b></li>
              <li><span>Personel</span><b>{counters.data?.staff ?? "…"}</b></li>
              <li><span>Tedarikçi</span><b>{counters.data?.suppliers ?? "…"}</b></li>
              <li><span>Ay içi fatura</span><b>{counters.data?.invoices_month ?? "…"}</b></li>
            </ul>
          )}
        </div>
        <nav className="card admin-nav">
          {RESOURCES.map((r) => (
            <button
              key={r.resource}
              className={r.resource === active ? "admin-nav-btn active" : "admin-nav-btn"}
              onClick={() => setActive(r.resource)}
            >
              {r.title}
            </button>
          ))}
        </nav>
      </aside>

      <section className="admin-main">
        <AdminSection
          key={def.resource}
          def={def}
          zoneLabels={zoneLabels}
          notify={notify}
          refreshCounters={counters.refresh}
        />
      </section>

      {toast && <div className={`toast toast-${toast.kind}`}>{toast.text}</div>}
    </div>
  );
}

function AdminSection({
  def,
  zoneLabels,
  notify,
  refreshCounters,
}: {
  def: ResourceDef;
  zoneLabels: Record<string, string>;
  notify: (text: string, kind?: "ok" | "err") => void;
  refreshCounters: () => void;
}) {
  const list = useResource(() => getAdminList(def.resource));
  const rows = list.data ?? [];
  const tableFields = def.fields.filter((f) => !f.hideInTable);

  const remove = async (id: string) => {
    try {
      await deleteAdmin(def.resource, id);
      notify(`${id} silindi`);
      list.refresh();
      refreshCounters();
    } catch {
      notify("Silme başarısız — backend kapalı olabilir", "err");
    }
  };

  return (
    <>
      <div className="card admin-table-card">
        <div className="card-head">
          <h2>{def.title}</h2>
          <span className="card-hint">
            {list.error ? "bağlantı yok" : `${rows.length} kayıt`}
          </span>
        </div>
        {list.error && (
          <div className="offline-note">
            Backend'e ulaşılamıyor — {def.title.toLowerCase()} listesi yüklenemedi.
          </div>
        )}
        {!list.error && rows.length === 0 && (
          <div className="empty">Henüz kayıt yok — aşağıdaki formdan ekleyin.</div>
        )}
        {rows.length > 0 && (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  {tableFields.map((f) => (
                    <th key={f.key}>{f.label}</th>
                  ))}
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const id = String(row[def.pk] ?? "");
                  return (
                    <tr
                      key={id}
                      className={
                        def.resource === "stock" && stockMismatch(row) ? "row-warn" : ""
                      }
                    >
                      {tableFields.map((f) =>
                        f.type === "checkbox" ? (
                          <td key={f.key}>
                            <span
                              className={
                                row[f.key]
                                  ? "state-badge tone-teal"
                                  : "state-badge tone-slate"
                              }
                            >
                              {row[f.key] ? "AKTİF" : "PASİF"}
                            </span>
                          </td>
                        ) : (
                          <td key={f.key}>{cellValue(row, f.key, zoneLabels)}</td>
                        ),
                      )}
                      <td className="td-actions">
                        <button className="btn btn-danger btn-sm" onClick={() => void remove(id)}>
                          Sil
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <AddForm
        def={def}
        onDone={(msg) => {
          notify(msg);
          list.refresh();
          refreshCounters();
        }}
        onError={(msg) => notify(msg, "err")}
      />
    </>
  );
}

function AddForm({
  def,
  onDone,
  onError,
}: {
  def: ResourceDef;
  onDone: (msg: string) => void;
  onError: (msg: string) => void;
}) {
  const blank = (): Record<string, string | boolean> =>
    Object.fromEntries(
      def.fields.map((f) => [
        f.key,
        f.type === "checkbox"
          ? Boolean(f.default)
          : f.defaultToday
            ? todayStr()
            : f.default !== undefined
              ? String(f.default)
              : "",
      ]),
    );
  const [values, setValues] = useState<Record<string, string | boolean>>(blank);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const fields: Record<string, unknown> = {};
    for (const f of def.fields) {
      const v = values[f.key];
      if (f.type === "checkbox") {
        fields[f.key] = Boolean(v);
        continue;
      }
      const s = String(v ?? "").trim();
      if (!s) continue;
      if (f.type === "number") {
        const n = Number(s.replace(",", "."));
        if (!Number.isFinite(n)) {
          onError(`${f.label} sayı olmalı`);
          return;
        }
        fields[f.key] = n;
      } else if (f.key === "lines") {
        const parsed = safeJson(s);
        if (!Array.isArray(parsed)) {
          onError("Kalemler geçerli bir JSON dizi olmalı", );
          return;
        }
        fields[f.key] = parsed;
      } else {
        fields[f.key] = s;
      }
    }
    const hasValue = Object.entries(fields).some(
      ([k, v]) => !(k === def.pk && !def.manualPk) && (typeof v !== "string" || v),
    );
    if (!hasValue) {
      onError("En az bir alan doldurun");
      return;
    }
    setBusy(true);
    try {
      await postAdmin(def.resource, fields);
      onDone(`${def.title} kaydı eklendi ✓`);
      setValues(blank());
    } catch {
      onError("Kaydedilemedi — backend kapalı olabilir");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card admin-form" onSubmit={(e) => void submit(e)}>
      <div className="card-head">
        <h2>Yeni ekle — {def.title}</h2>
        <span className="card-hint">
          {def.manualPk ? "ID elle verilir" : "ID boş bırakılırsa otomatik üretilir"}
        </span>
      </div>
      <div className="form-grid">
        {def.fields.map((f) =>
          f.type === "checkbox" ? (
            <label key={f.key} className="form-check">
              <input
                type="checkbox"
                checked={Boolean(values[f.key])}
                onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.checked }))}
              />
              {f.label}
            </label>
          ) : (
            <label key={f.key} className="form-field">
              <span>{f.label}</span>
              {f.type === "select" ? (
                <select
                  value={String(values[f.key] ?? "")}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                >
                  {f.options?.map(([val, lab]) => (
                    <option key={val} value={val}>
                      {lab}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={
                    f.type === "number"
                      ? "number"
                      : f.type === "date"
                        ? "date"
                        : f.type === "time"
                          ? "time"
                          : "text"
                  }
                  step={f.type === "number" ? "any" : undefined}
                  value={String(values[f.key] ?? "")}
                  placeholder={f.key === "lines" ? '[{"item":"Kıyma","qty":2,"unit":"kg","price":450}]' : undefined}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                />
              )}
            </label>
          ),
        )}
      </div>
      <div>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "Kaydediliyor…" : "Ekle"}
        </button>
      </div>
    </form>
  );
}
