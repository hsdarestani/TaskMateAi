import { FormEvent, useState } from 'react';

import { useAuth } from '../context/AuthContext';

export default function LoginForm() {
  const { login, loading, error } = useAuth();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('changeme');
  const [scope, setScope] = useState<'system' | 'org'>('system');
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage(null);

    try {
      await login({ username, password, scope });
      setMessage('Welcome back. Secure console unlocked.');
    } catch {
      // errors are surfaced via context state
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-md flex-col gap-4 rounded-3xl border border-white/5 bg-slate-900/60 p-6 backdrop-blur">
      <div>
        <h1 className="text-2xl font-semibold text-white">Sign in</h1>
        <p className="text-sm text-slate-400">Authenticate with your TaskMate administrator credentials.</p>
      </div>
      <fieldset className="flex items-center justify-between rounded-2xl border border-white/5 bg-slate-900/60 p-2 text-xs uppercase tracking-wide text-slate-300">
        <legend className="sr-only">Role scope</legend>
        <label className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-2xl px-3 py-2 transition ${scope === 'system' ? 'bg-emerald-500/20 text-emerald-100' : 'hover:bg-white/5'}`}>
          <input
            type="radio"
            name="scope"
            value="system"
            checked={scope === 'system'}
            onChange={() => setScope('system')}
            className="hidden"
          />
          System Admin
        </label>
        <label className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-2xl px-3 py-2 transition ${scope === 'org' ? 'bg-cyan-500/20 text-cyan-100' : 'hover:bg-white/5'}`}>
          <input
            type="radio"
            name="scope"
            value="org"
            checked={scope === 'org'}
            onChange={() => setScope('org')}
            className="hidden"
          />
          Org Admin
        </label>
      </fieldset>
      <label className="text-xs uppercase tracking-wide text-slate-400">
        Username
        <input
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
          autoComplete="username"
        />
      </label>
      <label className="text-xs uppercase tracking-wide text-slate-400">
        Password
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
          autoComplete="current-password"
        />
      </label>
      {error && <p className="rounded-2xl bg-rose-500/10 px-4 py-2 text-xs text-rose-200">{error}</p>}
      {message && !error && <p className="rounded-2xl bg-emerald-500/10 px-4 py-2 text-xs text-emerald-200">{message}</p>}
      <button
        type="submit"
        disabled={loading}
        className="mt-2 w-full rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? 'Authenticating…' : 'Access console'}
      </button>
    </form>
  );
}
