'use client';

import { useEffect, useState } from 'react';
import AdminGuard from '@/components/AdminGuard';
import AppShell from '@/components/AppShell';
import Card from '@/components/ui/Card';
import Link from 'next/link';
import { useConvertCurrency, CurrencyToggle } from '@/components/CurrencyToggle';
import {
  Activity,
  Pause,
  Play,
  Users,
  Settings,
  TrendingUp,
  Target,
  BarChart3,
  AlertTriangle,
  Loader2,
} from 'lucide-react';

interface BotStatus {
  running: boolean;
  paused: boolean;
  pausedBy: string | null;
  pauseReason: string | null;
}

interface Stats {
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  avg_rr: number;
  trades_today_xauusd: number;
  trades_today_us100: number;
}

const defaultStats: Stats = {
  total_trades: 0,
  win_rate: 0,
  total_pnl: 0,
  avg_rr: 0,
  trades_today_xauusd: 0,
  trades_today_us100: 0,
};

function StatBlock({ label, value, color = 'text-text-primary' }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border border-border bg-bg p-3">
      <p className="font-display text-xs font-medium uppercase tracking-wider text-text-muted">{label}</p>
      <p className={`mt-1 font-display text-xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

export default function AdminDashboard() {
  const [botStatus, setBotStatus] = useState<BotStatus>({ running: true, paused: false, pausedBy: null, pauseReason: null });
  const [stats, setStats] = useState<Stats>(defaultStats);
  const [loading, setLoading] = useState(false);
  const [reason, setReason] = useState('');
  const { convert, symbol } = useConvertCurrency();

  useEffect(() => {
    fetchBotStatus();
    fetchStats();
    const interval = setInterval(() => {
      fetchBotStatus();
      fetchStats();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  async function fetchBotStatus() {
    try {
      const res = await fetch('/api/bot');
      if (res.ok) setBotStatus(await res.json());
    } catch { /* retry */ }
  }

  async function fetchStats() {
    try {
      const res = await fetch('/api/stats');
      if (res.ok) {
        const data = await res.json();
        setStats({
          total_trades: data.global?.total_trades ?? 0,
          win_rate: data.global?.win_rate ?? 0,
          total_pnl: data.global?.total_pnl ?? 0,
          avg_rr: data.global?.avg_rr ?? 0,
          trades_today_xauusd: data.today?.XAUUSD ?? 0,
          trades_today_us100: data.today?.US100 ?? 0,
        });
      }
    } catch { /* retry */ }
  }

  async function handleBotAction(action: 'pause' | 'resume') {
    setLoading(true);
    try {
      const res = await fetch('/api/bot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, reason: action === 'pause' ? reason : null }),
      });
      if (res.ok) {
        await fetchBotStatus();
        setReason('');
      }
    } catch { /* retry */ }
    finally { setLoading(false); }
  }

  const pnlSign = stats.total_pnl >= 0 ? '+' : '';
  const pnlColor = stats.total_pnl >= 0 ? 'text-profit' : 'text-loss';

  return (
    <AdminGuard requiredRole="owner">
      <AppShell>
        <div className="space-y-5 p-4 lg:p-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-display text-xl font-bold text-text-primary">Panneau Admin</h1>
              <p className="mt-0.5 text-sm text-text-muted">Contrôle et supervision du bot</p>
            </div>
            <CurrencyToggle />
          </div>

          {/* Bot Control */}
          <Card title="Contrôle du Bot">
            <div className="space-y-4">
              {/* Status */}
              <div className="flex items-center gap-3">
                <div className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium ${
                  botStatus.paused
                    ? 'bg-warning/10 text-warning'
                    : botStatus.running
                    ? 'bg-profit/10 text-profit'
                    : 'bg-loss/10 text-loss'
                }`}>
                  <Activity className="h-4 w-4" />
                  {botStatus.paused ? 'En pause' : botStatus.running ? 'En cours d\'exécution' : 'Arrêté'}
                </div>
                {botStatus.paused && botStatus.pauseReason && (
                  <div className="flex items-center gap-1.5 text-sm text-text-muted">
                    <AlertTriangle className="h-3.5 w-3.5 text-warning" />
                    Pause: {botStatus.pauseReason}
                  </div>
                )}
              </div>

              {/* Controls */}
              <div className="flex flex-wrap items-center gap-3">
                {!botStatus.paused && (
                  <input
                    type="text"
                    placeholder="Raison de la pause (optionnel)..."
                    value={reason}
                    onChange={e => setReason(e.target.value)}
                    className="flex-1 rounded-lg border border-border bg-bg px-3 py-2 font-display text-sm text-text-primary outline-none transition-colors focus:border-border-bright placeholder:text-text-muted min-w-48"
                  />
                )}
                {botStatus.paused ? (
                  <button
                    onClick={() => handleBotAction('resume')}
                    disabled={loading}
                    className="flex items-center gap-2 rounded-lg border border-profit/30 bg-profit/5 px-4 py-2 font-display text-sm font-medium text-profit transition-colors hover:bg-profit/15 disabled:opacity-50"
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                    Reprendre le bot
                  </button>
                ) : (
                  <button
                    onClick={() => handleBotAction('pause')}
                    disabled={loading}
                    className="flex items-center gap-2 rounded-lg border border-warning/30 bg-warning/5 px-4 py-2 font-display text-sm font-medium text-warning transition-colors hover:bg-warning/15 disabled:opacity-50"
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pause className="h-4 w-4" />}
                    Mettre en pause
                  </button>
                )}
              </div>
            </div>
          </Card>

          {/* Stats overview */}
          <Card title="Statistiques globales">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <StatBlock label="Total Trades" value={String(stats.total_trades)} />
              <StatBlock
                label="Win Rate"
                value={`${stats.win_rate.toFixed(1)}%`}
                color={stats.win_rate >= 50 ? 'text-profit' : 'text-loss'}
              />
              <StatBlock
                label="Total PnL"
                value={`${pnlSign}${convert(stats.total_pnl).toFixed(2)} ${symbol}`}
                color={pnlColor}
              />
              <StatBlock label="Avg R:R" value={`${stats.avg_rr.toFixed(2)}R`} />
              <StatBlock
                label="XAUUSD Auj."
                value={`${stats.trades_today_xauusd}/5`}
                color={stats.trades_today_xauusd >= 5 ? 'text-loss' : 'text-text-primary'}
              />
              <StatBlock
                label="US100 Auj."
                value={`${stats.trades_today_us100}/5`}
                color={stats.trades_today_us100 >= 5 ? 'text-loss' : 'text-text-primary'}
              />
            </div>
          </Card>

          {/* Quick links */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Link
              href="/admin/users"
              className="flex items-center gap-4 rounded-xl border border-border bg-surface p-4 transition-all hover:border-border-bright hover:bg-surface-hover"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-info/10">
                <Users className="h-5 w-5 text-info" />
              </div>
              <div>
                <p className="font-display text-sm font-semibold text-text-primary">Utilisateurs</p>
                <p className="text-xs text-text-muted">Rôles et permissions</p>
              </div>
            </Link>

            <Link
              href="/admin/settings"
              className="flex items-center gap-4 rounded-xl border border-border bg-surface p-4 transition-all hover:border-border-bright hover:bg-surface-hover"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-warning/10">
                <Settings className="h-5 w-5 text-warning" />
              </div>
              <div>
                <p className="font-display text-sm font-semibold text-text-primary">Paramètres</p>
                <p className="text-xs text-text-muted">Configuration du bot</p>
              </div>
            </Link>

            <Link
              href="/performance"
              className="flex items-center gap-4 rounded-xl border border-border bg-surface p-4 transition-all hover:border-border-bright hover:bg-surface-hover"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-profit/10">
                <TrendingUp className="h-5 w-5 text-profit" />
              </div>
              <div>
                <p className="font-display text-sm font-semibold text-text-primary">Performance</p>
                <p className="text-xs text-text-muted">Analytics avancés</p>
              </div>
            </Link>
          </div>
        </div>
      </AppShell>
    </AdminGuard>
  );
}
