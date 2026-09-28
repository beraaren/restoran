import { TerminalShell } from '../../components/TerminalShell';
import './KdsPage.css';

const COLUMNS = ['Kuyruk', 'Hazırlanıyor', 'Hazır', 'Servis'] as const;

/** Mutfak ekranı kabuğu — placeholder kuyruk kolonları. */
export function KdsPage() {
  return (
    <TerminalShell title="Mutfak">
      <div className="kds-columns">
        {COLUMNS.map((c) => (
          <section key={c} className="kds-column">
            <header className="kds-column-header">{c}</header>
            <p className="kds-empty">Ticket yok</p>
          </section>
        ))}
      </div>
    </TerminalShell>
  );
}
