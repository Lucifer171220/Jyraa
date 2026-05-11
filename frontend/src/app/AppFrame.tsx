'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  ArrowRightOnRectangleIcon,
  Bars3BottomLeftIcon,
  CpuChipIcon,
  FolderIcon,
  HomeModernIcon,
  MagnifyingGlassIcon,
  PlusCircleIcon,
  RectangleGroupIcon,
  ShieldCheckIcon,
  Squares2X2Icon,
  CalendarDaysIcon,
} from '@heroicons/react/24/outline';
import { AuthProvider, useAuth } from '@/lib/auth-context';
import { BrandMark } from '@/components/BrandMark';

const publicRoutes = new Set(['/login', '/register']);

const navItems = [
  {
    href: '/',
    label: 'Dashboard',
    description: 'Workspace pulse and recent activity',
    icon: HomeModernIcon,
  },
  {
    href: '/projects',
    label: 'Projects',
    description: 'Scopes, ownership, and delivery lanes',
    icon: FolderIcon,
  },
  {
    href: '/boards',
    label: 'Boards',
    description: 'Execution views across active teams',
    icon: RectangleGroupIcon,
  },
  {
    href: '/search',
    label: 'Search',
    description: 'JQL-like issue search and saved filters',
    icon: MagnifyingGlassIcon,
  },
  {
    href: '/planning',
    label: 'Planning',
    description: 'Sprints, capacity, roadmaps, and Gantt views',
    icon: CalendarDaysIcon,
  },
  {
    href: '/dashboards',
    label: 'Dashboards',
    description: 'Shared dashboards and operational gadgets',
    icon: Squares2X2Icon,
  },
  {
    href: '/admin',
    label: 'Admin',
    description: 'ACLs, webhooks, templates, audit, and tasks',
    icon: ShieldCheckIcon,
  },
  {
    href: '/agents',
    label: 'Agents',
    description: 'Prompt-driven automation and AI workflow control',
    icon: CpuChipIcon,
  },
];

function getRouteMeta(pathname: string) {
  if (pathname === '/') {
    return {
      eyebrow: 'Workspace dashboard',
      title: 'Command center',
      description: 'Monitor project health, jump into active boards, and keep momentum visible.',
    };
  }

  if (pathname.startsWith('/projects/new')) {
    return {
      eyebrow: 'Project setup',
      title: 'Create a new project',
      description: 'Define the scope, naming, and structure for a new delivery space.',
    };
  }

  if (pathname.startsWith('/projects/')) {
    return {
      eyebrow: 'Project workspace',
      title: 'Project details',
      description: 'Track boards, workflow health, and what this team is shipping next.',
    };
  }

  if (pathname.startsWith('/projects')) {
    return {
      eyebrow: 'Project directory',
      title: 'All projects',
      description: 'Browse, open, and create the workspaces that power your delivery flow.',
    };
  }

  if (pathname.startsWith('/boards/')) {
    return {
      eyebrow: 'Delivery board',
      title: 'Board execution',
      description: 'Move work forward, inspect issue flow, and keep the team aligned.',
    };
  }

  if (pathname.startsWith('/issues/')) {
    return {
      eyebrow: 'Issue workspace',
      title: 'Issue details',
      description: 'Work directly inside a single issue with full-page editing, comments, and time tracking.',
    };
  }

  if (pathname.startsWith('/boards')) {
    return {
      eyebrow: 'Board library',
      title: 'All boards',
      description: 'Jump between team boards without losing context or navigation momentum.',
    };
  }

  if (pathname.startsWith('/search')) {
    return {
      eyebrow: 'Advanced search',
      title: 'Search and filters',
      description: 'Build JQL-like issue searches, save reusable filters, and move directly into matching work.',
    };
  }

  if (pathname.startsWith('/planning')) {
    return {
      eyebrow: 'Planning room',
      title: 'Sprints and roadmaps',
      description: 'Shape sprint capacity, release roadmaps, and Gantt-style timelines from one planning surface.',
    };
  }

  if (pathname.startsWith('/dashboards')) {
    return {
      eyebrow: 'Dashboard studio',
      title: 'Dashboards and gadgets',
      description: 'Create shared dashboard views and compose operational gadgets for team visibility.',
    };
  }

  if (pathname.startsWith('/admin')) {
    return {
      eyebrow: 'Admin control room',
      title: 'Security and integrations',
      description: 'Manage ACLs, webhooks, templates, audit events, rate limits, and background tasks.',
    };
  }

  if (pathname.startsWith('/agents')) {
    return {
      eyebrow: 'Automation control',
      title: 'Agent orchestration',
      description: 'Run prompt-driven workflows for project setup, assignment, review, and notification automation.',
    };
  }

  return {
    eyebrow: 'Workspace',
    title: 'ZYRAA',
    description: 'Project management, issue tracking, and team coordination in one place.',
  };
}

function ShellLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || '/';
  const router = useRouter();
  const { token, user, logout, isLoading } = useAuth();

  if (publicRoutes.has(pathname)) {
    return <>{children}</>;
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <div className="rounded-3xl border border-slate-200 bg-white/80 px-6 py-5 text-sm text-slate-600 shadow-[0_18px_40px_rgba(15,23,42,0.08)]">
          Loading your workspace...
        </div>
      </div>
    );
  }

  const meta = getRouteMeta(pathname);
  const userInitial = (user?.display_name || user?.username || 'Z').charAt(0).toUpperCase();

  if (!token) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen text-slate-900">
      <aside className="hidden bg-[linear-gradient(180deg,#09111f_0%,#0c1729_55%,#0b2431_100%)] text-white lg:fixed lg:inset-y-0 lg:flex lg:w-[19.5rem] lg:flex-col lg:border-r lg:border-white/8">
        <div className="border-b border-white/8 px-6 py-7">
          <BrandMark compact />
          <p className="mt-4 text-sm leading-6 text-slate-300">
            A deliberate workspace for planning, issue flow, and calm operational visibility.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="rounded-[1.75rem] border border-white/8 bg-white/5 px-4 py-4">
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.28em] text-cyan-200/90">
              Navigation
            </p>
            <nav className="mt-4 space-y-2">
            {navItems.map((item) => {
              const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`group flex items-start gap-3 rounded-2xl px-4 py-3 transition ${
                    isActive
                      ? 'bg-white text-slate-950 shadow-[0_18px_35px_rgba(255,255,255,0.12)]'
                      : 'text-slate-200 hover:bg-white/8 hover:text-white'
                  }`}
                >
                  <span className={`mt-0.5 rounded-xl p-2 ${isActive ? 'bg-slate-950 text-white' : 'bg-white/10 text-cyan-200'}`}>
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold">{item.label}</span>
                    <span className={`mt-1 block text-xs leading-5 ${isActive ? 'text-slate-500' : 'text-slate-400'}`}>
                      {item.description}
                    </span>
                  </span>
                </Link>
              );
            })}
            </nav>
          </div>

          <div className="mt-8 rounded-[1.75rem] border border-cyan-400/20 bg-[linear-gradient(160deg,rgba(14,165,233,0.18),rgba(15,23,42,0.22))] p-5 shadow-[0_24px_60px_rgba(2,132,199,0.12)]">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-200">
              Quick launch
            </p>
            <h3 className="mt-3 text-lg font-semibold text-white">Start a new workspace</h3>
            <p className="mt-2 text-sm leading-6 text-slate-200">
              Create a project, shape its workflow, and move from planning into execution faster.
            </p>
            <button
              onClick={() => router.push('/projects/new')}
              className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-50"
            >
              <PlusCircleIcon className="h-5 w-5" />
              Create project
            </button>
          </div>
        </div>

        <div className="border-t border-white/8 px-5 py-5">
          <div className="flex items-center gap-3 rounded-2xl bg-white/6 px-4 py-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/12 text-sm font-semibold text-white">
              {userInitial}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-white">
                {user?.display_name || user?.username || 'Workspace user'}
              </p>
              <p className="truncate text-xs text-slate-400">{user?.email || 'Signed in to ZYRAA'}</p>
            </div>
            <button
              onClick={logout}
              className="rounded-xl p-2 text-slate-300 transition hover:bg-white/10 hover:text-white"
              aria-label="Sign out"
            >
              <ArrowRightOnRectangleIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      </aside>

      <div className="lg:pl-[19.5rem]">
        <header className="sticky top-0 z-20 border-b border-white/70 bg-white/72 backdrop-blur-xl">
          <div className="px-4 py-4 sm:px-6 lg:px-8">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex items-start gap-3">
                <div className="rounded-2xl bg-slate-950 p-3 text-white shadow-[0_16px_32px_rgba(15,23,42,0.16)] lg:hidden">
                  <Bars3BottomLeftIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="eyebrow text-sky-600">
                    {meta.eyebrow}
                  </p>
                  <h1 className="app-title mt-2 text-2xl font-semibold text-slate-950">{meta.title}</h1>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{meta.description}</p>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                {navItems.map((item) => {
                  const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                        isActive
                          ? 'button-primary text-white'
                          : 'button-secondary text-slate-700'
                      }`}
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>
        </header>

        <main className="px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}

export function AppFrame({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <ShellLayout>{children}</ShellLayout>
    </AuthProvider>
  );
}
