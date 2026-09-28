import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../store/auth';
import './TerminalShell.css';

function useClock(): string {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);
  return now.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

interface TerminalShellProps {
  title: string;
  children: ReactNode;
}

/** Garson/KDS terminal kabuğu: tam ekran, minimal üst bar (başlık + rol + saat + çıkış). */
export function TerminalShell({ title, children }: TerminalShellProps) {
  const employee = useAuth((s) => s.employee);
  const venue = useAuth((s) => s.venue);
  const signOut = useAuth((s) => s.signOut);
  const navigate = useNavigate();
  const clock = useClock();

  return (
    <div className="terminal">
      <header className="terminal-bar">
        <span className="terminal-title">{title}</span>
        {venue ? <span className="muted">{venue.name}</span> : null}
        <div className="terminal-right">
          {employee ? <span className="badge badge-accent">{employee.role.name}</span> : null}
          <span className="terminal-clock">{clock}</span>
          <button
            type="button"
            className="btn"
            onClick={() => {
              signOut();
              navigate('/login', { replace: true });
            }}
          >
            Çıkış
          </button>
        </div>
      </header>
      <main className="terminal-content">{children}</main>
    </div>
  );
}
