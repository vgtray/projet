'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { timeAgo } from '@/lib/utils';
import { Play, Pause } from 'lucide-react';
import { useToast } from '@/components/Toast';

type UserRole = 'owner' | 'admin' | 'user';

interface BotState {
  bot_active: boolean;
  bot_paused: boolean;
  last_analyzed_XAUUSD: string | null;
  last_analyzed_US100: string | null;
}

const defaultState: BotState = {
  bot_active: false,
  bot_paused: false,
  last_analyzed_XAUUSD: null,
  last_analyzed_US100: null,
};

function isRecentlyActive(lastAnalyzed: string | null): boolean {
  if (!lastAnalyzed) return false;
  const diff = Date.now() - new Date(lastAnalyzed).getTime();
  return diff < 8 * 60 * 1000; // 8 minutes (> 5 min between M5 candles)
}

export default function BotStatus() {
  const [state, setState] = useState<BotState>(defaultState);
  const [toggling, setToggling] = useState(false);
  const [userRole, setUserRole] = useState<UserRole>('user');
  const { showToast } = useToast();

  const isActive =
    isRecentlyActive(state.last_analyzed_XAUUSD) ||
    isRecentlyActive(state.last_analyzed_US100);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await fetch('/api/status');
        if (res.ok) setState(await res.json());
      } catch { /* retry next interval */ }
    }

    async function fetchUserRole() {
      try {
        const res = await fetch('/api/auth/me');
        if (res.ok) {
          const data = await res.json();
          setUserRole(data.role || 'user');
        }
      } catch { /* not logged in */ }
    }

    fetchStatus();
    fetchUserRole();
    const interval = setInterval(fetchStatus, 10_000);
    return () => clearInterval(interval);
  }, []);

  async function togglePause() {
    if (toggling) return;
    setToggling(true);
    try {
      const action = state.bot_paused ? 'resume' : 'pause';
      const res = await fetch('/api/bot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      if (res.ok) {
        setState(prev => ({ ...prev, bot_paused: action === 'pause' }));
        showToast(action === 'pause' ? 'Bot en pause' : 'Bot reprit', 'success');
      } else {
        showToast('Erreur lors de l\'action', 'error');
      }
    } catch { 
      showToast('Erreur de connexion', 'error');
    }
    setToggling(false);
  }

  const canControl = userRole === 'owner' || userRole === 'admin';

  return (
    <div className="flex items-center gap-3">
      {/* Status dot */}
      <div className="flex items-center gap-2">
        <div className="relative flex items-center">
          <span
            className={cn(
              'h-2.5 w-2.5 rounded-full',
              isActive && !state.bot_paused ? 'bg-profit animate-pulse-dot' : 'bg-loss'
            )}
          />
          {isActive && !state.bot_paused && (
            <span className="absolute h-2.5 w-2.5 animate-ping rounded-full bg-profit/40" />
          )}
        </div>
        <span
          className={cn(
            'font-display text-sm font-semibold',
            isActive && !state.bot_paused ? 'text-profit' : 'text-loss'
          )}
        >
          {state.bot_paused ? 'Pause' : isActive ? 'Bot actif' : 'Bot inactif'}
        </span>
      </div>

      {/* Last analyzed */}
      <div className="hidden items-center gap-3 text-xs text-text-muted md:flex">
        <span>
          XAU: {timeAgo(state.last_analyzed_XAUUSD)}
        </span>
        <span className="text-border-bright">|</span>
        <span>
          US100: {timeAgo(state.last_analyzed_US100)}
        </span>
      </div>

      {/* Toggle button - only for admin/owner */}
      {canControl && (
        <button
          onClick={togglePause}
          disabled={toggling}
          className={cn(
            'flex items-center gap-1.5 rounded-md border px-3 py-1.5 font-display text-xs font-medium transition-colors disabled:opacity-50',
            state.bot_paused
              ? 'border-profit/30 bg-profit-dim/20 text-profit hover:bg-profit-dim/40'
              : 'border-warning/30 bg-warning-dim/20 text-warning hover:bg-warning-dim/40'
          )}
        >
          {state.bot_paused ? (
            <>
              <Play className="h-3 w-3" />
              Resume
            </>
          ) : (
            <>
              <Pause className="h-3 w-3" />
              Pause
            </>
          )}
        </button>
      )}
    </div>
  );
}
