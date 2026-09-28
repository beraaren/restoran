# Restoran OS — Web (apps/web)

Yeni ürün kabuğu: Vite 7 + React 18 + TypeScript. Kökteki eski `web/` panelinden bağımsızdır; o legacy'dir.

## Çalıştırma

```bash
npm install
cp .env.example .env   # istenirse; default zaten http://localhost:8100
npm run dev            # http://localhost:5174  (eski panel 5173'ü işgal edebilir)
npm run typecheck
npm run build          # tsc -b && vite build → dist/
npm run preview
```

## Rotalar

- `/login` — PIN pad ile çalışan girişi (mekan slug + kullanıcı/kart input'u gömülü)
- `/admin/*` — patron/müdür paneli kabuğu (AppShell sol menü; tüm sayfalar "Faz 1'de geliyor" placeholder)
  - `/admin/settings/zones` — eski ZoneEditor faz 1'de buraya taşınacak
- `/floor/*` — garson adisyon terminali kabuğu (placeholder masa grid'i, TerminalShell)
- `/kds/*` — mutfak ekranı kabuğu (placeholder kuyruk kolonları, TerminalShell)

## Auth akışı

- `POST {API}/auth/login/pin` → `{venue_slug, identifier, pin}`; başarılıysa token + claims Zustand store'a (`src/store/auth.ts`) yazılır, token `localStorage`'da (`ros.token`).
- `src/api/client.ts`: her istekte `Authorization: Bearer` ekler; 401'de oturumu kapatır ve `/login`'e yönlendirir.
- `src/router/RequireAuth.tsx`: token yoksa tüm korumalı rotalar `/login`'e düşer.

## Tasarım sistemi

Açık tema, düz CSS (UI framework yok). Token'lar `src/styles/tokens.css`, reset/tipografi `src/styles/base.css`. Bileşenler yalnızca CSS custom property kullanır.

## Kütüphaneler

react-router-dom v7, @tanstack/react-query v5, zustand v5. Başka bir şey eklenmedi.
