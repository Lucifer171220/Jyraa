'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { dashboardAPI } from '@/lib/api';
import { Dashboard } from '@/types';
import { useAuth } from '@/lib/auth-context';

export default function DashboardsPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [selected, setSelected] = useState<Dashboard | null>(null);
  const [name, setName] = useState('Delivery cockpit');
  const [description, setDescription] = useState('A shared dashboard for team health and delivery flow.');

  useEffect(() => {
    if (!token) {
      router.push('/login');
      return;
    }
    void loadDashboards();
  }, [token, router]);

  const loadDashboards = async () => {
    const response = await dashboardAPI.getAll();
    const items = response.data as Dashboard[];
    setDashboards(items);
    if (items[0]) {
      const detail = await dashboardAPI.getById(items[0].dashboard_id);
      setSelected(detail.data as Dashboard);
    }
  };

  const createDashboard = async () => {
    const response = await dashboardAPI.create({ name, description, is_shared: true, layout_config: '{}' });
    const dashboard = response.data as Dashboard;
    await dashboardAPI.addGadget(dashboard.dashboard_id, {
      gadget_type: 'issue_stats',
      title: 'Issue health',
      config: JSON.stringify({ metric: 'open_vs_done' }),
      width: 4,
      height: 3,
    });
    await loadDashboards();
  };

  const addGadget = async (type: string, title: string) => {
    if (!selected) return;
    await dashboardAPI.addGadget(selected.dashboard_id, {
      gadget_type: type,
      title,
      config: JSON.stringify({ generated: true }),
      width: 4,
      height: 3,
    });
    const detail = await dashboardAPI.getById(selected.dashboard_id);
    setSelected(detail.data as Dashboard);
  };

  return (
    <div className="space-y-6">
      <section className="hero-panel rounded-[2rem] p-6">
        <p className="eyebrow text-violet-600">Dashboards and gadgets</p>
        <h2 className="app-title mt-2 text-3xl font-semibold text-slate-950">Operational dashboards</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          Create shared dashboards, add gadgets, and keep delivery signals close to the team.
        </p>
      </section>

      <section className="grid gap-6 xl:grid-cols-[340px_1fr]">
        <aside className="glass-panel rounded-[2rem] p-6">
          <p className="text-sm font-semibold text-slate-900">Create dashboard</p>
          <input value={name} onChange={(event) => setName(event.target.value)} className="mt-4 w-full rounded-2xl border border-slate-300 px-4 py-2.5 text-sm" />
          <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={3} className="mt-3 w-full rounded-2xl border border-slate-300 px-4 py-2.5 text-sm" />
          <button onClick={() => void createDashboard()} className="button-primary mt-4 w-full rounded-2xl px-4 py-2.5 text-sm font-semibold text-white">
            Create
          </button>

          <div className="mt-8 space-y-3">
            <p className="eyebrow text-sky-600">Your dashboards</p>
            {dashboards.map((dashboard) => (
              <button
                key={dashboard.dashboard_id}
                onClick={async () => {
                  const detail = await dashboardAPI.getById(dashboard.dashboard_id);
                  setSelected(detail.data as Dashboard);
                }}
                className="soft-panel block w-full rounded-2xl px-4 py-3 text-left"
              >
                <p className="text-sm font-semibold text-slate-950">{dashboard.name}</p>
                <p className="mt-1 text-xs text-slate-500">{dashboard.is_shared ? 'Shared' : 'Private'}</p>
              </button>
            ))}
          </div>
        </aside>

        <main className="glass-panel rounded-[2rem] p-6">
          {selected ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="eyebrow text-emerald-600">Selected dashboard</p>
                  <h3 className="mt-2 text-2xl font-semibold text-slate-950">{selected.name}</h3>
                  <p className="mt-2 text-sm text-slate-600">{selected.description}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button onClick={() => void addGadget('issue_stats', 'Issue health')} className="button-secondary rounded-2xl px-3 py-2 text-xs font-semibold">Issue stats</button>
                  <button onClick={() => void addGadget('assigned_work', 'Assigned work')} className="button-secondary rounded-2xl px-3 py-2 text-xs font-semibold">Assigned work</button>
                  <button onClick={() => void addGadget('sprint_capacity', 'Sprint capacity')} className="button-secondary rounded-2xl px-3 py-2 text-xs font-semibold">Sprint capacity</button>
                </div>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {(selected.gadgets || []).map((gadget) => (
                  <div key={gadget.gadget_id} className="metric-card rounded-[1.5rem] p-5">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{gadget.gadget_type}</p>
                    <h4 className="mt-3 text-lg font-semibold text-slate-950">{gadget.title}</h4>
                    <p className="mt-2 text-sm leading-6 text-slate-600">Configured gadget block, ready for richer metric rendering.</p>
                    <button
                      onClick={async () => {
                        await dashboardAPI.deleteGadget(selected.dashboard_id, gadget.gadget_id);
                        const detail = await dashboardAPI.getById(selected.dashboard_id);
                        setSelected(detail.data as Dashboard);
                      }}
                      className="mt-4 text-xs font-semibold text-rose-600"
                    >
                      Remove gadget
                    </button>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="rounded-3xl border border-dashed border-slate-300 px-6 py-16 text-center text-sm text-slate-500">
              Create a dashboard to start adding gadgets.
            </div>
          )}
        </main>
      </section>
    </div>
  );
}
