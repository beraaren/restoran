import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../store/auth';

/** Token yoksa /login'e yönlendirir; varsa çocuk route'u render eder. */
export function RequireAuth() {
  const token = useAuth((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <Outlet />;
}
