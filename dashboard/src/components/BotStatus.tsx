'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { timeAgo } from '@/lib/utils';
import { Play, Pause, Bot } from 'lucide-react';

interface BotState {
  active: boolean;
  paused: boolean;
  last_analyzed_xauusd: string | null;
  last_analyzed_us100: string | null;
}

const defaultState: BotState = {
  active: false,
  paused: false,
  last_analyzed_xauusd: null,
  last_analyzed_us100: null,
};

function isRecentlyActive(lastAnalyzed: string | null): boolean {
  if (!lastAnalyzed) return false;
  const diff = Date.now() - new Date(lastAnalyzed).getTime();
  return diff < 8 * 60 * 1000; // 8 minutes (> 5 min between M5 candles)
}

export default function BotStatus() {
  const [state, setState] = useState<BotState>(defaultState);
  const [toggling, setToggling] = useState(false);

  const isActive =
    isRecentlyActive(state.last_analyzed_xauusd) ||
    isRecentlyActive(state.last_analyzed_us100);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await fetch('/api/status');
        if (res.ok) setState(await res.json());
      } catch { /* retry next interval */ }
    }

    fetchStatus();
    const interval = setInterval(fetchStatus, 10_000);
    return () => clearInterval(interval);
  }, []);

  async function togglePause() {
    if (toggling) return;
    setToggling(true);
    try {
      const action = state.paused ? 'resume' : 'pause';
      const res = await fetch('/api/bot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      if (res.ok) {
        const data = await res.json();
        setState(prev => ({ ...prev, paused: action === 'pause' }));
      }
    } catch { /* silently fail */ }
    setToggling(false);
  }

  return (
    <div className="flex items-center gap-3">
      {/* Status dot */}
      <div className="flex items-center gap-2">
        <div className="relative flex items-center">
          <span
            className={cn(
              'h-2.5 w-2.5 rounded-full',
              isActive && !state.paused ? 'bg-profit animate-pulse-dot' : 'bg-loss'
            )}
          />
          {isActive && !state.paused && (
            <span className="absolute h-2.5 w-2.5 animate-ping rounded-full bg-profit/40" />
          )}
        </div>
        <span
          className={cn(
            'font-display text-sm font-semibold',
            isActive && !state.paused ? 'text-profit' : 'text-loss'
          )}
        >
          {state.paused ? 'Pause' : isActive ? 'Bot actif' : 'Bot inactif'}
        </span>
      </div>

      {/* Last analyzed */}
      <div className="hidden items-center gap-3 text-xs text-text-muted md:flex">
        <span>
          XAU: {timeAgo(state.last_analyzed_xauusd)}
        </span>
        <span className="text-border-bright">|</span>
        <span>
          US100: {timeAgo(state.last_analyzed_us100)}
        </span>
      </div>

      {/* Toggle button */}
      <button
        onClick={togglePause}
        disabled={toggling}
        className={cn(
          'flex items-center gap-1.5 rounded-md border px-3 py-1.5 font-display text-xs font-medium transition-colors disabled:opacity-50',
          state.paused
            ? 'border-profit/30 bg-profit-dim/20 text-profit hover:bg-profit-dim/40'
            : 'border-warning/30 bg-warning-dim/20 text-warning hover:bg-warning-dim/40'
        )}
      >
        {state.paused ? (
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
    </div>
  );
}
