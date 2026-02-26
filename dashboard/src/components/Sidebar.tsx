'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { authClient } from '@/lib/auth-client';
import BotStatus from '@/components/BotStatus';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Radio,
  ScrollText,
  TrendingUp,
  Settings,
  Users,
  LogOut,
  Shield,
} from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session } = authClient.useSession();
  const [role, setRole] = useState<string>('user');

  useEffect(() => {
    if (!session?.user) return;
    fetch('/api/auth/me')
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (d?.role) setRole(d.role); })
      .catch(() => {});
  }, [session]);

  const handleSignOut = async () => {
    await authClient.signOut();
    router.push('/login');
  };

  const isAdmin = role === 'admin' || role === 'owner';
  const isOwner = role === 'owner';

  const navLinks = [
    { href: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
    { href: '/performance', label: 'Performance', icon: TrendingUp },
    ...(isAdmin
      ? [
          { href: '/signals', label: 'Signals', icon: Radio },
          { href: '/logs', label: 'Logs', icon: ScrollText },
        ]
      : []),
  ];

  const adminLinks = isOwner
    ? [
        { href: '/admin', label: 'Panneau Admin', icon: Shield, exact: true },
        { href: '/admin/users', label: 'Utilisateurs', icon: Users },
        { href: '/admin/settings', label: 'Paramètres', icon: Settings },
      ]
    : [];

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname === href || pathname.startsWith(href + '/');

  return (
    <aside className="hidden lg:flex flex-col fixed left-0 top-0 h-screen w-60 border-r border-border bg-surface z-40">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 border-b border-border px-4 shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-profit/10 text-profit">
          <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="2">
            <path d="M2 20h20M5 20V9l4 3 4-8 4 5 3-4v15" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div className="flex flex-col">
          <span className="font-display text-sm font-bold leading-tight text-text-primary">Trade Bot</span>
          <span className="font-display text-xs text-text-muted leading-tight">SMC / ICT</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        <p className="mb-2 px-2 font-display text-xs font-semibold uppercase tracking-wider text-text-muted">
          Navigation
        </p>
        {navLinks.map(({ href, label, icon: Icon, exact }) => {
          const active = isActive(href, exact);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 font-display text-sm font-medium transition-all',
                active
                  ? 'bg-profit/10 text-profit'
                  : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}

        {adminLinks.length > 0 && (
          <>
            <div className="my-3 pt-3 border-t border-border">
              <p className="mb-2 px-2 font-display text-xs font-semibold uppercase tracking-wider text-text-muted">
                Admin
              </p>
            </div>
            {adminLinks.map(({ href, label, icon: Icon, exact }) => {
              const active = isActive(href, exact);
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 font-display text-sm font-medium transition-all',
                    active
                      ? 'bg-info/10 text-info'
                      : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary'
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {label}
                </Link>
              );
            })}
          </>
        )}
      </nav>

      {/* Footer */}
      <div className="border-t border-border px-3 py-3 space-y-3 shrink-0">
        <BotStatus compact />
        <div className="flex items-center gap-2">
          <div className="flex-1 min-w-0">
            <p className="truncate font-display text-xs font-medium text-text-secondary">
              {session?.user?.name || session?.user?.email || '—'}
            </p>
            {role !== 'user' && (
              <p className="font-display text-xs text-text-muted capitalize">{role}</p>
            )}
          </div>
          <button
            onClick={handleSignOut}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-text-muted transition-colors hover:bg-surface-hover hover:text-text-primary"
            title="Se déconnecter"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
