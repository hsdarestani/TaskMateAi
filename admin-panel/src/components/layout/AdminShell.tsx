import { Outlet } from 'react-router-dom';

import SidebarNav from './SidebarNav';
import TopBar from './TopBar';

export default function AdminShell() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 px-4 py-8 text-slate-100">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-8 xl:flex-row">
        <SidebarNav />
        <main className="flex-1 space-y-8">
          <TopBar />
          <section className="space-y-8">
            <Outlet />
          </section>
        </main>
      </div>
    </div>
  );
}
