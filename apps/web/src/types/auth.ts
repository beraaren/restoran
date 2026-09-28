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

// --- backend tel (wire) tipleri: /auth/login/pin bu şekli alır/verir ---
export interface LoginPinRequest {
  venue_slug: string;
  employee_id_or_card: string;
  pin: string;
  terminal_id?: string;
}

export interface EmployeeWire {
  employee_id: string;
  full_name: string;
  card_code: string | null;
  role: string;
  permissions: string[];
  venue_id: string;
  active: boolean;
}

export interface LoginPinResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  employee: EmployeeWire;
}

/** GET /auth/me ham JWT claims'ini döner. */
export interface MeClaims {
  sub: string;
  venue_id: string;
  role: string;
  perms: string[];
  terminal_id: string | null;
  iat: number;
  exp: number;
}

export interface AuthSession {
  token: string;
  employee: Employee;
  venue: Venue;
}
