import { TerminalShell } from '../../components/TerminalShell';
import './FloorPage.css';

const TABLES = Array.from({ length: 18 }, (_, i) => i + 1);

/** Garson adisyon terminali kabuğu — placeholder masa planı. */
export function FloorPage() {
  return (
    <TerminalShell title="Salon">
      <div className="floor-grid">
        {TABLES.map((n) => (
          <div key={n} className="floor-table">
            Masa {n}
            <small className="muted">Boş</small>
          </div>
        ))}
      </div>
    </TerminalShell>
  );
}
