import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

interface Props {
  allowedScopes?: Array<'system' | 'org'>;
}

export default function ProtectedRoute({ allowedScopes }: Props) {
  const { token, scope } = useAuth();
  const location = useLocation();

  if (!token) {
    return <Navigate to="/panel/login" replace state={{ from: location }} />;
  }

  if (allowedScopes && scope && !allowedScopes.includes(scope)) {
    return <Navigate to="/panel/dashboard" replace />;
  }

  return <Outlet />;
}
