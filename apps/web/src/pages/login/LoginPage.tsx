import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { loginWithPin } from '../../api/auth';
import { ApiError } from '../../api/client';
import { useAuth } from '../../store/auth';
import { PinPad } from '../../components/PinPad';
import './Login.css';

export function LoginPage() {
  const [venueSlug, setVenueSlug] = useState('demo');
  const [identifier, setIdentifier] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const signIn = useAuth((s) => s.signIn);
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: loginWithPin,
    onSuccess: (session) => {
      signIn({ token: session.token, employee: session.employee, venue: session.venue });
      navigate('/admin', { replace: true });
    },
    onError: (err: unknown) => {
      setPin('');
      if (err instanceof ApiError && err.status === 403) {
        setError('Bu hesap pasif görünüyor. Yöneticinize başvurun.');
      } else if (err instanceof ApiError && err.status === 401) {
        setError('PIN veya kullanıcı hatalı.');
      } else {
        setError('Sunucuya ulaşılamadı. API kapalı olabilir.');
      }
    },
  });

  const submit = (submittedPin: string) => {
    if (!identifier.trim()) {
      setError('Önce kullanıcıınızı seçin.');
      return;
    }
    setError(null);
    mutation.mutate({ venue_slug: venueSlug.trim() || 'demo', identifier: identifier.trim(), pin: submittedPin });
  };

  return (
    <div className="login">
      <form
        className="login-card card"
        onSubmit={(e) => {
          e.preventDefault();
          if (pin.length >= 4) submit(pin);
        }}
      >
        <h1 className="login-title">Restoran OS</h1>
        <p className="muted">Devam etmek için hesabınızı seçin ve PIN girin.</p>

        <label className="login-field">
          <span>Mekan</span>
          <input
            value={venueSlug}
            onChange={(e) => setVenueSlug(e.target.value)}
            placeholder="venue_slug"
            autoComplete="off"
          />
        </label>

        <label className="login-field">
          <span>Kullanıcı / Kart</span>
          <input
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="kullanıcı adı veya kart kodu"
            autoComplete="off"
          />
        </label>

        <PinPad
          value={pin}
          onChange={setPin}
          onSubmit={submit}
          error={error}
          disabled={mutation.isPending}
        />
      </form>
    </div>
  );
}
