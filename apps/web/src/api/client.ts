import { useAuth } from '../store/auth';

export const API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8100').replace(
  /\/+$/,
  '',
);

/** HTTP durumu + gövdeden üretilen hata; çağıran taraf mesaj basar. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `HTTP ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  /** Token gönderilmesin isteniyorsa (login gibi) false. */
  auth?: boolean;
  signal?: AbortSignal;
}

/**
 * fetch sarmalayıcı: JSON seriye/anti-seri, JWT header, 401'de oturumu kapatıp /login.
 */
export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true, signal } = opts;
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  const token = useAuth.getState().token;
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!res.ok) {
    if (res.status === 401 && auth) {
      useAuth.getState().signOut();
      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    let detail: unknown = res.statusText;
    try {
      detail = await res.json();
      if (typeof detail === 'object' && detail && 'detail' in detail) {
        detail = (detail as { detail: unknown }).detail;
      }
    } catch {
      /* gövde JSON değil → statusText kalır */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
