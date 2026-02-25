'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import BotStatus from '@/components/BotStatus';
import { cn } from '@/lib/utils';
import { LayoutDashboard, Radio, ScrollText, LogOut } from 'lucide-react';
import { authClient } from '@/lib/auth-client';

const nav = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/signals', label: 'Signals', icon: Radio },
  { href: '/logs', label: 'Logs', icon: ScrollText },
];

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session } = authClient.useSession();

  const handleSignOut = async () => {
    await authClient.signOut();
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-screen-2xl items-center justify-between px-4 lg:px-6">
        {/* Logo + Nav */}
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-profit/10 text-profit">
              <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="2">
                <path d="M2 20h20M5 20V9l4 3 4-8 4 5 3-4v15" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span className="font-display text-base font-bold tracking-tight text-text-primary">
              Trade Bot
              <span className="ml-1.5 text-text-muted">SMC/ICT</span>
            </span>
          </Link>

          {/* Navigation */}
          <nav className="hidden items-center gap-1 md:flex">
            {nav.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-1.5 font-display text-sm font-medium transition-colors',
                    active
                      ? 'bg-surface text-text-primary'
                      : 'text-text-muted hover:text-text-secondary'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bot Status */}
        <div className="flex items-center gap-4">
          {session?.user && (
            <span className="text-sm text-zinc-400 hidden md:block">
              {session.user.name || session.user.email}
            </span>
          )}
          <button
            onClick={handleSignOut}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium text-zinc-400 hover:text-white transition-colors"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden md:inline">Sign Out</span>
          </button>
          <BotStatus />
        </div>
      </div>
    </header>
  );
}
