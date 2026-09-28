import { api } from './client';
import type {
  AuthSession,
  LoginPinRequest,
  LoginPinResponse,
  MeClaims,
} from '../types/auth';

function toSession(res: LoginPinResponse, req: LoginPinRequest): AuthSession {
  return {
    token: res.access_token,
    employee: {
      id: res.employee.employee_id,
      full_name: res.employee.full_name,
      role: { name: res.employee.role, permissions: res.employee.permissions },
    },
    // backend venue nesnesi döndürmüyor; giriş formundaki slug + venue_id ile kuruyoruz
    venue: {
      id: res.employee.venue_id,
      name: req.venue_slug,
      slug: req.venue_slug,
    },
  };
}

export async function loginWithPin(payload: LoginPinRequest): Promise<AuthSession> {
  const res = await api<LoginPinResponse>('/auth/login/pin', {
    method: 'POST',
    body: payload,
    auth: false,
  });
  return toSession(res, payload);
}

export function fetchMe(): Promise<MeClaims> {
  return api<MeClaims>('/auth/me');
}
