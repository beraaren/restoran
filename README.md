# Restoran Akış İzleme Sistemi

Kamera görüntülerinden mutfak–servis akışının durum geçişlerini çıkarıp POS
(kasa) kayıtlarıyla çaprazlayan; uyuşmazlıkları "kayıp-kaçak" anomali olarak
₺ karşılığıyla raporlayan sistem. Patronun fiziksel denetim yükünü almaya
yönelik PoC/iskelet.

## Hızlı başlat (uçtan uca demo)

```bash
# 1) Python kurulumu (bir kez)
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"

# 2) Test videosu üret (bir kez; bus.jpg crop'larıyla PASS geçiş senaryosu)
.venv/bin/python tools/make_test_video.py

# 3) Demo: API + vision stream + mock POS + anomali raporu
.venv/bin/python tools/demo.py

# 4) Panel (ayrı terminal)
cd web && npm install && npm run dev   # http://localhost:5173
# Panelde bölge çizim sekmesi: http://localhost:5173/#zones
```

Demo sonunda konsolda anomali dökümü basılır; API :8100'de açık kalır,
panel onu okur. Bölge çizim aracı panelin ikinci sekmesindedir
(PUT /scene ile backend'e kaydedilir).

## Mimari (özet)

```
video/kamera ──YOLO+ByteTrack──► PassCounter ──► VisionEvent ─┐
                                                              ├─► Reconciler ─► Anomaly ─► Panel
POS (kontrat) ──adaptör/mock────► PosEvent ───────────────────┘
                                        │
                                Aktör durum makineleri (plate/table/customer/chef/waiter)
```

- **Ingestion Contract** (`src/restoran/contracts/events.py`): POS adaptörleri
  bu şemaya uyar; uymayan POS ile çalışılmaz. Minimum olay seti:
  TABLE_OPEN / ORDER_LINE_ADD / TICKET_FIRE / LINE_VOID / PAYMENT / TABLE_CLOSE.
  Zorunlu: UTC-ms timestamp, idempotency key (`event_id`), Decimal para.
- **Zone config** (`config/scene.*.json`): masalar/bölgeler/PASS çizgisi
  normalized (0..1) poligon ve çizgilerle tanımlı. Kamera değişince sadece
  config güncellenir — panelin "Bölge Çizimi" sekmesinden elle çizilir.
- **PASS sözleşmesi**: çizgi a(üst)→b(alt) çizilir; +1 tarafı (sol) mutfak.
  Soldan sağa geçiş `direction=out` = üretimden çıkış.
- **Reconciler** (`core/reconcile.py`): zaman pencereli consume-eşleştirme.
  ticket'ı olmayan PASS çıkışı → TICKETSIZ_URETIM; penceresi dolup karşılık
  bulamayan ticket → URETILMEYEN_SIPARIS; adisyonsuz dolu masa → ACILMAMIS_MASA.
  Pencereler env: `TICKET_TO_PLATE_S` (180), `PLATE_TO_TICKET_S` (120),
  `SEATING_WITHOUT_OPEN_S` (300). `CALIBRATION_S>0` iken anomaliler
  suppressed=True üretilir (kalibrasyon modu).
- **Depolama**: SQLite (dev) / Postgres (`docker compose up -d`;
  `DATABASE_URL=postgresql+psycopg://restoran:restoran@localhost:5433/restoran`).

## API

| Endpoint | Açıklama |
|---|---|
| `POST /ingest/pos` | PosEvent listesi (idempotent) |
| `POST /ingest/vision` | VisionEvent listesi |
| `GET /anomalies` | anomali akışı (`?kind=`, `?include_suppressed=`) |
| `GET /state` | aktör durumları + KPI sayaçları |
| `GET /events/recent` | canlı şerit tamponu |
| `GET/PUT /scene` | zone config oku/yaz |
| `WS /ws` | tüm event/anomali/durum yayınları |

## Komutlar

```bash
# videodan event üret (JSONL veya API'ye stream)
.venv/bin/python -m restoran.vision.runner data/pass_people.mp4 \
    --scene config/scene.passpeople.json --out data/vision_events.jsonl
.venv/bin/python -m restoran.vision.runner data/pass_people.mp4 \
    --scene config/scene.passpeople.json --http http://localhost:8100/ingest/vision \
    --stream --speed 4 --force-class plate   # demo harness

# mock POS'u JSONL'e ya da API'ye yaz
.venv/bin/python -m restoran.pos.mock --out data/pos_events.jsonl
.venv/bin/python -m restoran.pos.mock --http http://localhost:8100/ingest/pos

# testler
.venv/bin/python tests/smoke_reconcile.py
.venv/bin/python tests/test_pass_counter.py
```

## Mevcut sınırlar / faz planı

- **Faz A-B (bu repo):** PASS geçiş sayımı, mock POS, mutabakat, panel, çizim
  aracı, kişi→ürün sınıf atlaması yok (COCO'da `plate` sınıfı yok; demo
  videosu `--force-class` hilesiyle kişi crop'larıyla üretimi simüle eder).
- **Faz C:** Roboflow `plate-and-cup-detection` (~600 görsel) + 300-500 kendi
  kareyle YOLO fine-tune → gerçek tabak/bardak tespiti.
- **Personel/müşteri ayrımı:** `botsort.yaml` + `with_reid: true` (ultralytics
  yerleşik Re-ID) + vardiya eşleşmesi.
- **Faz D:** LINE_VOID temelli iptal tuzağı kuralı, ödeme kaçışı, kalibrasyon
  UI'ı, çok kamera/şube.
- **Lisans uyarısı:** Ultralytics YOLO **AGPL-3.0**. Ticari SaaS dağıtımında
  Ultralytics lisansı satın alınmalı ya da MIT alternatif modele geçilmeli.
  Roboflow/HF dataset lisansları ayrıca kontrol edilmeli.

## Ekip notları

- IP/kod bu repoda; teslim yalnızca yazılı sözleşme sonrasında.
- Para alanları Decimal, saat UTC-ms — mutabakatta taviz yok.
- Yeni anomali kuralı = Reconciler'a pencere + kural, test = smoke'e senaryo.
