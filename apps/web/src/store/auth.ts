import { create } from 'zustand';
import type { Employee, Venue } from '../types/auth';

const TOKEN_KEY = 'ros.token';
const EMPLOYEE_KEY = 'ros.employee';
const VENUE_KEY = 'ros.venue';

function readJSON<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export interface AuthState {
  token: string | null;
  employee: Employee | null;
  venue: Venue | null;
  /** POST /auth/login/pin başarılıysa çağrılır; localStorage'a yazar. */
  signIn: (args: { token: string; employee: Employee; venue: Venue }) => void;
  /** Token'ı ve claims'i siler; login'e yönlendirme çağıranın işi. */
  signOut: () => void;
  isAuthenticated: () => boolean;
}

export const useAuth = create<AuthState>((set, get) => ({
  token: localStorage.getItem(TOKEN_KEY),
  employee: readJSON<Employee>(EMPLOYEE_KEY),
  venue: readJSON<Venue>(VENUE_KEY),

  signIn: ({ token, employee, venue }) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(EMPLOYEE_KEY, JSON.stringify(employee));
    localStorage.setItem(VENUE_KEY, JSON.stringify(venue));
    set({ token, employee, venue });
  },

  signOut: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMPLOYEE_KEY);
    localStorage.removeItem(VENUE_KEY);
    set({ token: null, employee: null, venue: null });
  },

  isAuthenticated: () => Boolean(get().token),
}));
