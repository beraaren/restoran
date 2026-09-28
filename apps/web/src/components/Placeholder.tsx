import './Placeholder.css';

interface PlaceholderProps {
  title: string;
  note?: string;
}

/** "Faz 1'de geliyor" sayfa kartı. */
export function Placeholder({ title, note }: PlaceholderProps) {
  return (
    <section className="placeholder">
      <h1 className="placeholder-title">{title}</h1>
      <span className="badge">Faz 1&apos;de geliyor</span>
      <p className="muted">{note ?? 'Bu ekranın gerçek içeriği bir sonraki fazda bağlanacak.'}</p>
    </section>
  );
}
