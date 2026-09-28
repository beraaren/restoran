import './PinPad.css';

interface PinPadProps {
  value: string;
  onChange: (next: string) => void;
  onSubmit: (pin: string) => void;
  /** Hata mesajı gösterilir ve giriş kutusu sarsılır. */
  error?: string | null;
  minLength?: number;
  maxLength?: number;
  disabled?: boolean;
}

const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9'] as const;

/**
 * Standart POS PIN pad'i: 1-9, temizle, 0, giriş. Giriş maskelenir.
 */
export function PinPad({
  value,
  onChange,
  onSubmit,
  error,
  minLength = 4,
  maxLength = 8,
  disabled = false,
}: PinPadProps) {
  const press = (key: string) => {
    if (disabled) return;
    if (value.length < maxLength) onChange(value + key);
  };

  const clear = () => {
    if (disabled) return;
    onChange('');
  };

  const enter = () => {
    if (disabled || value.length < minLength) return;
    onSubmit(value);
  };

  return (
    <div className="pinpad">
      {/* key, hata her değiştiğinde elemanı yeniden monte eder → shake animasyonu tekrar tetiklenir */}
      <div
        key={error ?? 'ok'}
        className={`pinpad-display${error ? ' shake' : ''}${value ? '' : ' is-empty'}`}
        aria-live="polite"
      >
        {value ? '•'.repeat(value.length) : 'PIN girin'}
      </div>
      {error ? <p className="error-text">{error}</p> : null}
      <div className="pinpad-grid">
        {KEYS.map((k) => (
          <button key={k} type="button" className="pinpad-key" disabled={disabled} onClick={() => press(k)}>
            {k}
          </button>
        ))}
        <button type="button" className="pinpad-key is-clear" disabled={disabled} onClick={clear}>
          Temizle
        </button>
        <button type="button" className="pinpad-key" disabled={disabled} onClick={() => press('0')}>
          0
        </button>
        <button
          type="button"
          className="pinpad-key is-enter"
          disabled={disabled || value.length < minLength}
          onClick={enter}
        >
          Giriş
        </button>
      </div>
    </div>
  );
}
