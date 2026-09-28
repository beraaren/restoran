/** Backend auth sözleşmesiyle birebir eşleşen tipler (apps/api). */

export interface Role {
  name: string;
  permissions: string[];
}

export interface Employee {
  id: string;
  full_name: string;
  role: Role;
}

export interface Venue {
  id: string;
  name: string;
  slug: string;
}

export interface LoginPinRequest {
  venue_slug: string;
  identifier: string;
  pin: string;
}

export interface AuthSession {
  token: string;
  employee: Employee;
  venue: Venue;
}

/** GET /auth/me — token dışarıda, claims özeti aynı. */
export type MeClaims = Omit<AuthSession, 'token'>;
