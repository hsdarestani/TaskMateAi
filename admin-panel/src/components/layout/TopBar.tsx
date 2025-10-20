import { useAuth } from '../../context/AuthContext';

export default function TopBar() {
  const { username, scope, logout } = useAuth();
  const scopeLabel = scope === 'system' ? 'System Administrator' : scope === 'org' ? 'Organization Admin' : 'Administrator';

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-3xl border border-white/5 bg-slate-900/40 px-6 py-4 backdrop-blur">
      <div>
        <h2 className="text-lg font-semibold text-white">{scopeLabel} mode</h2>
        <p className="text-sm text-slate-400">Signed in as <span className="text-slate-200">{username ?? '—'}</span></p>
      </div>
      <button
        onClick={logout}
        className="rounded-full bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/20"
      >
        Sign out
      </button>
    </header>
  );
}
