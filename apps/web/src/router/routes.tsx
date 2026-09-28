import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from '../components/AppShell';
import { RequireAuth } from './RequireAuth';
import { LoginPage } from '../pages/login/LoginPage';
import { AdminPage } from '../pages/admin/AdminPage';
import { FloorPage } from '../pages/floor/FloorPage';
import { KdsPage } from '../pages/kds/KdsPage';
import { Placeholder } from '../components/Placeholder';

/**
 * Bilgi mimarisi:
 *  /login                 → PIN pad girişi ( herkese açık )
 *  /admin/*               → patron/müdür paneli kabuğu ( korumalı )
 *  /admin/settings/zones  → editör faz 1'de eski ZoneEditor'dan taşınacak
 *  /floor/*               → garson adisyon terminali kabuğu ( korumalı )
 *  /kds/*                 → mutfak ekranı kabuğu ( korumalı )
 */
export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      { path: '/', element: <Navigate to="/admin" replace /> },
      {
        path: '/admin',
        element: <AppShell />,
        children: [
          { index: true, element: <AdminPage title="Gösterge Paneli" /> },
          { path: 'menu', element: <AdminPage title="Menü & Ürünler" /> },
          { path: 'stock', element: <AdminPage title="Stok" /> },
          { path: 'purchasing', element: <AdminPage title="Satınalma" /> },
          { path: 'staff', element: <AdminPage title="Personel" /> },
          { path: 'cash', element: <AdminPage title="Kasa & Gün Sonu" /> },
          { path: 'audit', element: <AdminPage title="Denetim Merkezi" /> },
          { path: 'reports', element: <AdminPage title="Raporlar" /> },
          { path: 'channels', element: <AdminPage title="Kanallar" /> },
          {
            path: 'settings',
            element: (
              <Placeholder
                title="Ayarlar"
                note="Mekan, bölgeler ve terminal ayarları burada toplanacak."
              />
            ),
          },
          {
            path: 'settings/zones',
            element: (
              <Placeholder
                title="Bölgeler (Zones)"
                note="Eski ZoneEditor bileşeni faz 1'de buraya taşınacak."
              />
            ),
          },
        ],
      },
      { path: '/floor', element: <FloorPage /> },
      { path: '/floor/:zoneId', element: <FloorPage /> },
      { path: '/kds', element: <KdsPage /> },
      { path: '/kds/:stationId', element: <KdsPage /> },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);
