'use client';

import { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { TrendingUp, TrendingDown, Activity, BarChart3, Target, Zap } from 'lucide-react';

interface DailyPnL {
  date: string;
  pnl: number;
  trades: number;
  wins: number;
}

interface ByAsset {
  asset: string;
  total_trades: number;
  pnl: number;
  wins: number;
}

interface Stats {
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  avg_rr: number;
  max_drawdown: number;
  trades_today_xauusd: number;
  trades_today_us100: number;
  daily_pnl: DailyPnL[];
  by_asset: ByAsset[];
}

const defaultStats: Stats = {
  total_trades: 0,
  win_rate: 0,
  total_pnl: 0,
  avg_rr: 0,
  max_drawdown: 0,
  trades_today_xauusd: 0,
  trades_today_us100: 0,
  daily_pnl: [],
  by_asset: [],
};

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' });
}

const ASSET_COLORS = ['#22c55e', '#3b82f6', '#eab308', '#ef4444'];

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{value: number; name: string}>; label?: string }) => {
  if (active && payload && payload.length) {
    const value = payload[0].value;
    return (
      <div className="rounded-lg border border-border bg-surface px-3 py-2 shadow-xl">
        <p className="mb-1 font-display text-xs text-text-muted">{label}</p>
        <p className={`font-mono text-sm font-semibold ${value >= 0 ? 'text-profit' : 'text-loss'}`}>
          {value >= 0 ? '+' : ''}{value.toFixed(2)} €
        </p>
      </div>
    );
  }
  return null;
};

const PieTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{name: string; value: number; payload: {pnl: number}}> }) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border border-border bg-surface px-3 py-2 shadow-xl">
        <p className="font-display text-xs font-semibold text-text-primary">{payload[0].name}</p>
        <p className="font-mono text-xs text-text-secondary">{payload[0].value} trades</p>
        <p className={`font-mono text-xs ${payload[0].payload.pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
          PnL: {payload[0].payload.pnl >= 0 ? '+' : ''}{payload[0].payload.pnl.toFixed(2)} €
        </p>
      </div>
    );
  }
  return null;
};

interface KpiCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  valueColor?: string;
  sub?: string;
}

function KpiCard({ label, value, icon, valueColor = 'text-text-primary', sub }: KpiCardProps) {
  return (
    <div className="kpi-card flex flex-col gap-3 rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between">
        <span className="font-display text-xs font-semibold uppercase tracking-wider text-text-muted">{label}</span>
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-hover text-text-muted">
          {icon}
        </div>
      </div>
      <div>
        <span className={`font-display text-2xl font-bold ${valueColor}`}>{value}</span>
        {sub && <p className="mt-0.5 font-display text-xs text-text-muted">{sub}</p>}
      </div>
    </div>
  );
}

function DailyLimitBar({ label, used, max = 2 }: { label: string; used: number; max?: number }) {
  const pct = Math.min((used / max) * 100, 100);
  const color = pct >= 100 ? 'bg-loss' : pct >= 50 ? 'bg-warning' : 'bg-profit';
  return (
    <div className="flex items-center gap-3">
      <span className="w-20 shrink-0 font-display text-xs font-medium text-text-muted">{label}</span>
      <div className="flex flex-1 items-center gap-2">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-hover">
          <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
        </div>
        <span className="w-8 shrink-0 font-mono text-xs text-text-secondary">{used}/{max}</span>
      </div>
    </div>
  );
}

export default function StatsBar() {
  const [stats, setStats] = useState<Stats>(defaultStats);

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();
        setStats({
          total_trades: data.global?.total_trades ?? 0,
          win_rate: data.global?.win_rate ?? 0,
          total_pnl: data.global?.total_pnl ?? 0,
          avg_rr: data.global?.avg_rr ?? 0,
          max_drawdown: data.global?.max_drawdown ?? 0,
          trades_today_xauusd: data.today?.XAUUSD ?? 0,
          trades_today_us100: data.today?.US100 ?? 0,
          daily_pnl: data.chart?.daily_pnl ?? [],
          by_asset: data.chart?.by_asset ?? [],
        });
      } catch { /* silently retry next interval */ }
    }

    fetchStats();
    const interval = setInterval(fetchStats, 30_000);
    return () => clearInterval(interval);
  }, []);

  const pnlSign = stats.total_pnl >= 0 ? '+' : '';
  const pnlColor = stats.total_pnl >= 0 ? 'text-profit' : 'text-loss';

  const chartData = stats.daily_pnl.map(d => ({
    date: formatDate(d.date),
    PnL: Math.round(d.pnl * 100) / 100,
  }));

  const assetData = stats.by_asset.map(a => ({
    name: a.asset,
    value: a.total_trades,
    pnl: a.pnl,
  }));

  const pnlMin = chartData.length > 0 ? Math.min(...chartData.map(d => d.PnL)) : 0;
  const pnlMax = chartData.length > 0 ? Math.max(...chartData.map(d => d.PnL)) : 0;
  const areaColor = (pnlMax + pnlMin) >= 0 ? '#22c55e' : '#ef4444';

  return (
    <div className="space-y-4">
      {/* Row 1: 4 KPI cards */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label="Total PnL"
          value={`${pnlSign}${stats.total_pnl.toFixed(2)} €`}
          icon={stats.total_pnl >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
          valueColor={pnlColor}
          sub={`Max DD: ${Math.abs(stats.max_drawdown).toFixed(2)} €`}
        />
        <KpiCard
          label="Win Rate"
          value={`${stats.win_rate.toFixed(1)}%`}
          icon={<Target className="h-4 w-4" />}
          valueColor={stats.win_rate >= 50 ? 'text-profit' : stats.win_rate >= 40 ? 'text-warning' : 'text-loss'}
          sub={`${stats.total_trades} trades total`}
        />
        <KpiCard
          label="Total Trades"
          value={String(stats.total_trades)}
          icon={<BarChart3 className="h-4 w-4" />}
          sub={`${stats.trades_today_xauusd + stats.trades_today_us100} aujourd'hui`}
        />
        <KpiCard
          label="Avg Risk/Reward"
          value={`${stats.avg_rr.toFixed(2)}R`}
          icon={<Activity className="h-4 w-4" />}
          valueColor={stats.avg_rr >= 1.5 ? 'text-profit' : stats.avg_rr >= 1 ? 'text-warning' : 'text-loss'}
          sub="Ratio moyen"
        />
      </div>

      {/* Row 2: Daily limits + Charts */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {/* Daily limits + quick stats */}
        <div className="rounded-xl border border-border bg-surface p-4 space-y-4">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-warning" />
            <h3 className="font-display text-xs font-semibold uppercase tracking-wider text-text-secondary">
              Quotas du jour
            </h3>
          </div>
          <div className="space-y-3">
            <DailyLimitBar label="XAUUSD" used={stats.trades_today_xauusd} />
            <DailyLimitBar label="US100" used={stats.trades_today_us100} />
          </div>
          <div className="border-t border-border pt-3 space-y-2">
            <div className="flex justify-between">
              <span className="font-display text-xs text-text-muted">Max Drawdown</span>
              <span className="font-mono text-xs text-loss">-{Math.abs(stats.max_drawdown).toFixed(2)} €</span>
            </div>
            <div className="flex justify-between">
              <span className="font-display text-xs text-text-muted">Avg R:R</span>
              <span className="font-mono text-xs text-text-primary">{stats.avg_rr.toFixed(2)}R</span>
            </div>
          </div>
        </div>

        {/* PnL Area Chart */}
        <div className="rounded-xl border border-border bg-surface p-4">
          <h3 className="mb-3 font-display text-xs font-semibold uppercase tracking-wider text-text-secondary">
            PnL Quotidien (30j)
          </h3>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={140}>
              <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={areaColor} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={areaColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#52525b', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fill: '#52525b', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={v => `${v}€`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="PnL"
                  stroke={areaColor}
                  strokeWidth={2}
                  fill="url(#pnlGrad)"
                  dot={false}
                  activeDot={{ r: 4, fill: areaColor, stroke: '#0a0a0f', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-36 items-center justify-center text-xs text-text-muted">
              Aucune donnée disponible
            </div>
          )}
        </div>

        {/* Asset distribution */}
        <div className="rounded-xl border border-border bg-surface p-4">
          <h3 className="mb-3 font-display text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Répartition Assets
          </h3>
          {assetData.length > 0 ? (
            <ResponsiveContainer width="100%" height={140}>
              <PieChart>
                <Pie
                  data={assetData}
                  cx="50%"
                  cy="50%"
                  innerRadius={35}
                  outerRadius={55}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {assetData.map((_, i) => (
                    <Cell key={i} fill={ASSET_COLORS[i % ASSET_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltip />} />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: '11px', color: '#71717a', fontFamily: 'Space Grotesk' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-36 items-center justify-center text-xs text-text-muted">
              Aucune donnée disponible
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
