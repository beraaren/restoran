import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../store/auth';
import './AppShell.css';

export const ADMIN_MENU = [
  { to: '/admin', label: 'Gösterge Paneli', end: true },
  { to: '/admin/menu', label: 'Menü & Ürünler' },
  { to: '/admin/stock', label: 'Stok' },
  { to: '/admin/purchasing', label: 'Satınalma' },
  { to: '/admin/staff', label: 'Personel' },
  { to: '/admin/cash', label: 'Kasa & Gün Sonu' },
  { to: '/admin/audit', label: 'Denetim Merkezi' },
  { to: '/admin/reports', label: 'Raporlar' },
  { to: '/admin/channels', label: 'Kanallar' },
  { to: '/admin/settings', label: 'Ayarlar' },
] as const;

/** Admin kabuğu: sol menü + üst bar (kullanıcı/rol rozeti, çıkış). */
export function AppShell() {
  const employee = useAuth((s) => s.employee);
  const venue = useAuth((s) => s.venue);
  const signOut = useAuth((s) => s.signOut);
  const navigate = useNavigate();

  const logout = () => {
    signOut();
    navigate('/login', { replace: true });
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          Restoran OS
          <small>{venue?.name ?? 'Yönetim'}</small>
        </div>
        <nav className="nav" aria-label="Yönetim menüsü">
          {ADMIN_MENU.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={'end' in item ? item.end : false}
              className={({ isActive }) => `nav-link${isActive ? ' is-active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <strong>{venue?.name ?? 'Restoran OS'}</strong>
          <div className="topbar-user">
            {employee ? (
              <>
                <span>{employee.full_name}</span>
                <span className="badge badge-accent">{employee.role.name}</span>
              </>
            ) : null}
            <button type="button" className="btn" onClick={logout}>
              Çıkış
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
