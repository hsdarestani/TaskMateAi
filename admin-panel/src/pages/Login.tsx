import { Navigate, useLocation, type Location } from 'react-router-dom';

import LoginForm from '../components/LoginForm';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const { token } = useAuth();
  const location = useLocation() as { state?: { from?: Location } };

  if (token) {
    const redirectTo = (location.state?.from as Location | undefined)?.pathname ?? '/panel/dashboard';
    return <Navigate to={redirectTo} replace />;
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 px-4 py-10 text-slate-100">
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center gap-10 text-center">
        <div className="space-y-4">
          <p className="text-sm font-semibold uppercase tracking-[0.4em] text-emerald-400">TaskMate Operator Console</p>
          <h1 className="text-4xl font-bold text-white sm:text-5xl">Stay ahead of operations</h1>
          <p className="text-base text-slate-400 sm:text-lg">
            Monitor productivity, billing, and communication across every organization with a single pane of glass.
          </p>
        </div>
        <LoginForm />
      </div>
    </div>
  );
}
