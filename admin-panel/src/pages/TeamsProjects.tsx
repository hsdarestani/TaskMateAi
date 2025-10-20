import { useEffect, useState } from 'react';

import Badge from '../components/Badge';
import PageHeader from '../components/PageHeader';
import api from '../lib/api';

interface ProjectNode {
  id: string;
  name: string;
  status: 'planning' | 'active' | 'blocked' | 'completed';
  assignments: { users: number; teams: number };
}

interface TeamNode {
  id: string;
  name: string;
  lead: string;
  projects: ProjectNode[];
}

interface OrgTree {
  id: string;
  organization: string;
  teams: TeamNode[];
}

const fallbackTree: OrgTree[] = [
  {
    id: 'org-1',
    organization: 'Aurora Studio',
    teams: [
      {
        id: 'team-1',
        name: 'Product Experience',
        lead: 'Sara Nikzad',
        projects: [
          { id: 'proj-1', name: 'Command Center', status: 'active', assignments: { users: 14, teams: 2 } },
          { id: 'proj-2', name: 'Telegram Inbox', status: 'planning', assignments: { users: 6, teams: 1 } }
        ]
      },
      {
        id: 'team-2',
        name: 'Automation',
        lead: 'Iman Ghaderi',
        projects: [
          { id: 'proj-3', name: 'Reminder ML upgrade', status: 'blocked', assignments: { users: 5, teams: 1 } }
        ]
      }
    ]
  },
  {
    id: 'org-2',
    organization: 'Moonlit AI',
    teams: [
      {
        id: 'team-3',
        name: 'Customer Success',
        lead: 'Daniel Vega',
        projects: [
          { id: 'proj-4', name: 'Onboarding academy', status: 'active', assignments: { users: 11, teams: 1 } },
          { id: 'proj-5', name: 'Referral experiments', status: 'completed', assignments: { users: 4, teams: 1 } }
        ]
      }
    ]
  }
];

const statusTone: Record<ProjectNode['status'], Parameters<typeof Badge>[0]['tone']> = {
  planning: 'warning',
  active: 'success',
  blocked: 'danger',
  completed: 'info'
};

export default function TeamsProjectsPage() {
  const [tree, setTree] = useState<OrgTree[]>(fallbackTree);

  useEffect(() => {
    let ignore = false;
    const fetchHierarchy = async () => {
      try {
        const { data } = await api.get<{ results: OrgTree[] }>('/api/admin/teams');
        if (ignore) return;
        if (Array.isArray(data.results)) {
          setTree(data.results);
        }
      } catch (err) {
        if (import.meta.env.DEV) {
          console.info('Using fallback team hierarchy', err);
        }
      }
    };
    fetchHierarchy();
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Teams & projects"
        subtitle="Inspect cross-team ownership, assignments, and delivery status."
      />
      <div className="space-y-4">
        {tree.map((org) => (
          <section key={org.id} className="space-y-4 rounded-3xl border border-white/5 bg-slate-900/40 p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-xl font-semibold text-white">{org.organization}</h3>
                <p className="text-sm text-slate-400">{org.teams.length} teams • {org.teams.reduce((acc, team) => acc + team.projects.length, 0)} projects</p>
              </div>
            </div>
            <div className="space-y-3">
              {org.teams.map((team) => (
                <div key={team.id} className="rounded-2xl border border-white/5 bg-slate-950/60 p-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-lg font-semibold text-white">{team.name}</p>
                      <p className="text-sm text-slate-400">Led by {team.lead}</p>
                    </div>
                    <Badge tone="info">{team.projects.length} active initiatives</Badge>
                  </div>
                  <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    {team.projects.map((project) => (
                      <div key={project.id} className="rounded-2xl border border-white/5 bg-slate-900/40 p-4">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h4 className="text-base font-semibold text-white">{project.name}</h4>
                            <p className="text-xs text-slate-400">
                              {project.assignments.users} users • {project.assignments.teams} teams assigned
                            </p>
                          </div>
                          <Badge tone={statusTone[project.status]}>{project.status}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
