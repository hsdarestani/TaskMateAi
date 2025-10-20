import { Fragment } from 'react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/panel/dashboard', label: 'Dashboard' },
  { to: '/panel/users', label: 'Users' },
  { to: '/panel/organizations', label: 'Organizations' },
  { to: '/panel/teams-projects', label: 'Teams & Projects' },
  { to: '/panel/payments', label: 'Payments' },
  { to: '/panel/analytics', label: 'Analytics' },
  { to: '/panel/blog', label: 'Blog CMS' },
  { to: '/panel/notifications', label: 'Notifications' }
];

export default function SidebarNav() {
  return (
    <aside className="flex w-full flex-col gap-6 rounded-3xl border border-white/5 bg-slate-900/60 p-6 backdrop-blur xl:w-72">
      <div>
        <span className="text-xs uppercase tracking-wide text-emerald-300/70">TaskMate</span>
        <h1 className="text-2xl font-semibold text-white">Control Center</h1>
      </div>
      <nav className="flex flex-col gap-2 text-sm font-medium">
        {navItems.map((item) => (
          <Fragment key={item.to}>
            <NavLink
              to={item.to}
              className={({ isActive }) =>
                `flex items-center justify-between rounded-2xl px-4 py-3 transition-colors ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-400/40'
                    : 'text-slate-300 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              <span>{item.label}</span>
              <span className="text-xs text-slate-500">→</span>
            </NavLink>
          </Fragment>
        ))}
      </nav>
      <div className="mt-auto rounded-2xl border border-white/10 bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 p-4 text-xs text-slate-300">
        Secure access for system operators and organization administrators. Activity is logged and auditable.
      </div>
    </aside>
  );
}
