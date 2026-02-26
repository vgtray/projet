'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { authClient } from '@/lib/auth-client';
import { cn } from '@/lib/utils';
import { LayoutDashboard, Radio, TrendingUp, ScrollText, Shield } from 'lucide-react';

export default function MobileNav() {
  const pathname = usePathname();
  const { data: session } = authClient.useSession();
  const [role, setRole] = useState<string>('user');

  useEffect(() => {
    if (!session?.user) return;
    fetch('/api/auth/me')
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (d?.role) setRole(d.role); })
      .catch(() => {});
  }, [session]);

  const isAdmin = role === 'admin' || role === 'owner';
  const isOwner = role === 'owner';

  const tabs = [
    { href: '/', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/performance', label: 'Perfs', icon: TrendingUp },
    ...(isAdmin
      ? [
          { href: '/signals', label: 'Signals', icon: Radio },
          { href: '/logs', label: 'Logs', icon: ScrollText },
        ]
      : []),
    ...(isOwner ? [{ href: '/admin', label: 'Admin', icon: Shield }] : []),
  ];

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t border-border bg-surface/95 backdrop-blur-md lg:hidden">
      {tabs.map(({ href, label, icon: Icon }) => {
        const active = isActive(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex flex-col items-center gap-1 px-3 py-1.5 transition-colors',
              active ? 'text-profit' : 'text-text-muted hover:text-text-secondary'
            )}
          >
            <Icon className="h-5 w-5" />
            <span className="font-display text-xs font-medium">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
