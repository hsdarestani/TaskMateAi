import { useEffect, useMemo, useState } from 'react';

import Badge from '../components/Badge';
import DataTable from '../components/DataTable';
import PageHeader from '../components/PageHeader';
import SearchInput from '../components/SearchInput';
import api from '../lib/api';

interface UserRow extends Record<string, unknown> {
  id: string;
  name: string;
  email: string;
  organization?: string;
  role: 'member' | 'team_manager' | 'org_admin' | 'system_admin';
  status: 'active' | 'invited' | 'suspended';
  lastSeen: string;
}

const fallbackUsers: UserRow[] = [
  {
    id: '1',
    name: 'Sara Nikzad',
    email: 'sara@aurora.studio',
    organization: 'Aurora Studio',
    role: 'org_admin',
    status: 'active',
    lastSeen: '2024-07-01T10:20:00Z'
  },
  {
    id: '2',
    name: 'Daniel Vega',
    email: 'daniel@moonlit.ai',
    organization: 'Moonlit AI',
    role: 'team_manager',
    status: 'active',
    lastSeen: '2024-07-05T08:35:00Z'
  },
  {
    id: '3',
    name: 'Layla Rahimi',
    email: 'layla@atlas.io',
    organization: 'Atlas Labs',
    role: 'member',
    status: 'invited',
    lastSeen: '—'
  }
];

export default function UsersPage() {
  const [users, setUsers] = useState<UserRow[]>(fallbackUsers);
  const [query, setQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');

  useEffect(() => {
    let ignore = false;
    const fetchUsers = async () => {
      try {
        const { data } = await api.get<{ results: UserRow[] }>('/api/admin/users');
        if (ignore) return;
        if (Array.isArray(data.results)) {
          setUsers(data.results);
        }
      } catch (err) {
        if (import.meta.env.DEV) {
          console.info('Using fallback users data', err);
        }
      }
    };

    fetchUsers();
    return () => {
      ignore = true;
    };
  }, []);

  const filtered = useMemo(() => {
    return users.filter((user) => {
      const matchesQuery = [user.name, user.email, user.organization].some((value) =>
        value?.toLowerCase().includes(query.toLowerCase())
      );
      const matchesRole = roleFilter === 'all' || user.role === roleFilter;
      return matchesQuery && matchesRole;
    });
  }, [users, query, roleFilter]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="User directory"
        subtitle="Search across all workspaces, elevate access, or resolve incidents."
        actions={
          <div className="flex flex-wrap gap-3">
            <SearchInput
              label="Search"
              placeholder="Search by name, email, or organization"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <label className="flex min-w-[160px] flex-col gap-2 text-xs uppercase tracking-wide text-slate-400">
              <span>Role</span>
              <select
                value={roleFilter}
                onChange={(event) => setRoleFilter(event.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none"
              >
                <option value="all">All roles</option>
                <option value="system_admin">System admin</option>
                <option value="org_admin">Org admin</option>
                <option value="team_manager">Team manager</option>
                <option value="member">Member</option>
              </select>
            </label>
          </div>
        }
      />
      <DataTable<UserRow>
        columns={[
          { key: 'name', label: 'Name' },
          { key: 'email', label: 'Email' },
          { key: 'organization', label: 'Organization' },
          {
            key: 'role',
            label: 'Role',
            render: (user) => <Badge tone="info">{user.role.replace(/_/g, ' ')}</Badge>
          },
          {
            key: 'status',
            label: 'Status',
            render: (user) => (
              <Badge tone={user.status === 'active' ? 'success' : user.status === 'invited' ? 'warning' : 'danger'}>
                {user.status}
              </Badge>
            )
          },
          {
            key: 'lastSeen',
            label: 'Last seen',
            render: (user) => (
              <span className="text-sm text-slate-300">
                {user.lastSeen === '—' ? '—' : new Date(user.lastSeen).toLocaleString()}
              </span>
            )
          }
        ]}
        data={filtered}
        emptyLabel="No users match your filters"
      />
    </div>
  );
}
