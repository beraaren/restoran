import { api } from './client';
import type { AuthSession, LoginPinRequest, MeClaims } from '../types/auth';

export function loginWithPin(payload: LoginPinRequest): Promise<AuthSession> {
  return api<AuthSession>('/auth/login/pin', { method: 'POST', body: payload, auth: false });
}

export function fetchMe(): Promise<MeClaims> {
  return api<MeClaims>('/auth/me');
}
