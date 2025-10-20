import { useEffect, useMemo, useState } from 'react';

import Badge from '../components/Badge';
import DataTable from '../components/DataTable';
import PageHeader from '../components/PageHeader';
import SearchInput from '../components/SearchInput';
import api from '../lib/api';

interface OrganizationRow extends Record<string, unknown> {
  id: string;
  name: string;
  owner: string;
  plan: 'trial' | 'starter' | 'growth' | 'enterprise';
  members: number;
  activeProjects: number;
  createdAt: string;
}

const fallbackOrganizations: OrganizationRow[] = [
  {
    id: 'org-1',
    name: 'Aurora Studio',
    owner: 'Sara Nikzad',
    plan: 'growth',
    members: 48,
    activeProjects: 12,
    createdAt: '2023-11-15T08:00:00Z'
  },
  {
    id: 'org-2',
    name: 'Moonlit AI',
    owner: 'Daniel Vega',
    plan: 'enterprise',
    members: 132,
    activeProjects: 27,
    createdAt: '2022-09-08T10:45:00Z'
  },
  {
    id: 'org-3',
    name: 'Atlas Labs',
    owner: 'Layla Rahimi',
    plan: 'starter',
    members: 15,
    activeProjects: 6,
    createdAt: '2024-01-02T09:30:00Z'
  }
];

export default function OrganizationsPage() {
  const [organizations, setOrganizations] = useState<OrganizationRow[]>(fallbackOrganizations);
  const [query, setQuery] = useState('');
  const [plan, setPlan] = useState('all');

  useEffect(() => {
    let ignore = false;
    const fetchOrganizations = async () => {
      try {
        const { data } = await api.get<{ results: OrganizationRow[] }>('/api/admin/orgs');
        if (ignore) return;
        if (Array.isArray(data.results)) {
          setOrganizations(data.results);
        }
      } catch (err) {
        if (import.meta.env.DEV) {
          console.info('Using fallback organization data', err);
        }
      }
    };

    fetchOrganizations();
    return () => {
      ignore = true;
    };
  }, []);

  const filtered = useMemo(() => {
    return organizations.filter((org) => {
      const matchesQuery = [org.name, org.owner].some((value) => value.toLowerCase().includes(query.toLowerCase()));
      const matchesPlan = plan === 'all' || org.plan === plan;
      return matchesQuery && matchesPlan;
    });
  }, [organizations, query, plan]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Organizations"
        subtitle="Manage billing plans, monitor membership, and review workspace structure."
        actions={
          <div className="flex flex-wrap gap-3">
            <SearchInput label="Search" placeholder="Search organizations" value={query} onChange={(event) => setQuery(event.target.value)} />
            <label className="flex min-w-[160px] flex-col gap-2 text-xs uppercase tracking-wide text-slate-400">
              <span>Plan</span>
              <select
                value={plan}
                onChange={(event) => setPlan(event.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none"
              >
                <option value="all">All plans</option>
                <option value="trial">Trial</option>
                <option value="starter">Starter</option>
                <option value="growth">Growth</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </label>
          </div>
        }
      />
      <DataTable<OrganizationRow>
        columns={[
          { key: 'name', label: 'Organization' },
          { key: 'owner', label: 'Owner' },
          {
            key: 'plan',
            label: 'Plan',
            render: (org) => (
              <Badge tone={org.plan === 'enterprise' ? 'info' : org.plan === 'growth' ? 'success' : org.plan === 'starter' ? 'warning' : 'danger'}>
                {org.plan}
              </Badge>
            )
          },
          {
            key: 'members',
            label: 'Members',
            render: (org) => <span className="text-sm text-slate-200">{org.members.toLocaleString()}</span>
          },
          {
            key: 'activeProjects',
            label: 'Active projects',
            render: (org) => <span className="text-sm text-slate-200">{org.activeProjects}</span>
          },
          {
            key: 'createdAt',
            label: 'Created',
            render: (org) => <span className="text-sm text-slate-200">{new Date(org.createdAt).toLocaleDateString()}</span>
          }
        ]}
        data={filtered}
        emptyLabel="No organizations found"
      />
    </div>
  );
}
