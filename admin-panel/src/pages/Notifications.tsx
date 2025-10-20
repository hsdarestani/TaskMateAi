import { FormEvent, useState } from 'react';

import Badge from '../components/Badge';
import PageHeader from '../components/PageHeader';
import api from '../lib/api';

const channels = [
  { id: 'telegram', label: 'Telegram bot' },
  { id: 'email', label: 'Email' },
  { id: 'in_app', label: 'In-app banner' }
];

export default function NotificationsPage() {
  const [audience, setAudience] = useState<'all' | 'org_admins' | 'system_admins'>('all');
  const [message, setMessage] = useState('');
  const [channel, setChannel] = useState<string>('telegram');
  const [rateLimit, setRateLimit] = useState(120);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const estimatedDuration = Math.ceil(message.length / 320) * Math.ceil(rateLimit / 60);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setFeedback(null);
    try {
      await api.post('/api/admin/notifications', { audience, message, channel, rate_limit_per_minute: rateLimit });
      setFeedback('Notification queued successfully.');
      setMessage('');
    } catch (err) {
      if (import.meta.env.DEV) {
        console.info('Simulating broadcast send', err);
        setFeedback('Notification queued (development mock).');
        setMessage('');
      } else {
        setFeedback('Failed to queue notification.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        subtitle="Broadcast updates to targeted administrators with rate-limit guardrails."
        actions={<Badge tone="warning">Throttle enforced at gateway</Badge>}
      />
      <section className="space-y-6 rounded-3xl border border-white/5 bg-slate-900/40 p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <label className="flex flex-col gap-2 text-xs uppercase tracking-wide text-slate-400">
            <span>Audience</span>
            <select
              value={audience}
              onChange={(event) => setAudience(event.target.value as typeof audience)}
              className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-emerald-400 focus:outline-none"
            >
              <option value="all">All users</option>
              <option value="org_admins">Organization admins</option>
              <option value="system_admins">System administrators</option>
            </select>
          </label>
          <fieldset className="flex flex-wrap gap-2 text-xs uppercase tracking-wide text-slate-400">
            <legend className="sr-only">Channel</legend>
            {channels.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setChannel(option.id)}
                className={`rounded-2xl px-4 py-2 text-xs font-semibold transition ${
                  channel === option.id ? 'bg-emerald-500 text-slate-950' : 'border border-white/10 text-slate-300 hover:bg-white/5'
                }`}
              >
                {option.label}
              </button>
            ))}
          </fieldset>
          <label className="flex flex-col gap-2 text-xs uppercase tracking-wide text-slate-400">
            <span>Message</span>
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              required
              className="h-40 rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-emerald-400 focus:outline-none"
              placeholder="Major release notes, maintenance, or guidance"
            />
          </label>
          <label className="flex flex-col gap-2 text-xs uppercase tracking-wide text-slate-400">
            <span>Rate limit (messages/min)</span>
            <input
              type="number"
              min={30}
              max={600}
              value={rateLimit}
              onChange={(event) => setRateLimit(Number(event.target.value))}
              className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-emerald-400 focus:outline-none"
            />
          </label>
          <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-sm text-slate-300">
            <p className="font-semibold text-white">Preview</p>
            <p className="mt-2 whitespace-pre-wrap text-slate-200">{message || 'Compose a message to preview tone and formatting.'}</p>
            <p className="mt-4 text-xs text-slate-400">
              Estimated completion: ~{estimatedDuration} minutes at {rateLimit} msgs/min via {channels.find((c) => c.id === channel)?.label}.
            </p>
          </div>
          {feedback && <p className="rounded-2xl bg-emerald-500/10 px-4 py-2 text-xs text-emerald-200">{feedback}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? 'Queueing…' : 'Send notification'}
          </button>
        </form>
      </section>
    </div>
  );
}
