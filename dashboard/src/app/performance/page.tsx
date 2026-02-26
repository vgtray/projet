'use client';

import { useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import Card from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import Badge from '@/components/ui/Badge';
import { useConvertCurrency, CurrencyToggle } from '@/components/CurrencyToggle';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend,
} from 'recharts';
import { TrendingUp, TrendingDown, Award, AlertTriangle, BarChart3 } from 'lucide-react';

interface DailyPnL {
  date: string;
  pnl: number;
  cumPnl: number;
  trades: number;
  wins: number;
}

interface AssetStat {
  asset: string;
  total_trades: number;
  wins: number;
  total_pnl: number;
  avg_pnl: number;
  win_rate: number;
}

interface PatternStat {
  pattern_type: string;
  total_trades: number;
  wins: number;
  win_rate: number;
  avg_rr: number;
  total_pnl: number;
}

interface Trade {
  id: number;
  asset: string;
  direction: string;
  entry_price: number;
  pnl: number;
  closed_reason: string | null;
  entry_time: string;
  closed_at: string;
}

interface PerfData {
  daily_pnl: DailyPnL[];
  by_asset: AssetStat[];
  by_pattern: PatternStat[];
  best_trade: Trade | null;
  worst_trade: Trade | null;
}

type Range = '30' | '60' | '90';

function fmtDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' });
}

function fmtPnL(v: number, convertFn?: (n: number) => number, sym?: string) {
  const converted = convertFn ? convertFn(v) : v;
  const s = sym ?? '€';
  return `${converted >= 0 ? '+' : ''}${converted.toFixed(2)} ${s}`;
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{value: number; name: string; color: string}>; label?: string }) => {
  const { convert, symbol } = useConvertCurrency();
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 shadow-xl">
      <p className="mb-1 font-display text-xs text-text-muted">{label}</p>
      {payload.map(p => (
        <p key={p.name} className="font-mono text-xs font-medium" style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' && p.name.toLowerCase().includes('pnl') ? fmtPnL(p.value, convert, symbol) : p.value}
        </p>
      ))}
    </div>
  );
};

function TradeCard({ trade, type }: { trade: Trade; type: 'best' | 'worst' }) {
  const { convert, symbol } = useConvertCurrency();
  const isProfit = trade.pnl >= 0;
  return (
    <div className="rounded-lg border border-border bg-bg p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {type === 'best' ? (
            <Award className="h-4 w-4 text-profit" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-loss" />
          )}
          <span className="font-display text-xs font-semibold uppercase tracking-wider text-text-muted">
            {type === 'best' ? 'Meilleur trade' : 'Pire trade'}
          </span>
        </div>
        <Badge variant={trade.direction === 'long' ? 'success' : 'danger'}>
          {trade.direction === 'long' ? '▲ LONG' : '▼ SHORT'}
        </Badge>
      </div>
      <div className="flex items-end justify-between">
        <div>
          <p className="font-display text-sm font-semibold text-text-primary">{trade.asset}</p>
          <p className="font-mono text-xs text-text-muted">{fmtDate(trade.entry_time)}</p>
        </div>
        <span className={`font-mono text-lg font-bold ${isProfit ? 'text-profit' : 'text-loss'}`}>
          {fmtPnL(trade.pnl, convert, symbol)}
        </span>
      </div>
    </div>
  );
}

const RANGE_BTNS: { label: string; value: Range }[] = [
  { label: '30j', value: '30' },
  { label: '60j', value: '60' },
  { label: '90j', value: '90' },
];

export default function PerformancePage() {
  const [data, setData] = useState<PerfData | null>(null);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState<Range>('30');
  const { convert, symbol } = useConvertCurrency();

  const chartFormatter = (v: number) => `${convert(v)}${symbol}`;

  useEffect(() => {
    fetch('/api/performance')
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setData(d); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const fmtPnLValue = (v: number) => {
    return fmtPnL(v, convert, symbol);
  };

  const rangeN = parseInt(range);
  const filteredDaily = (data?.daily_pnl ?? []).slice(-rangeN);

  // Recompute cumulative for filtered range
  let cum = 0;
  const chartData = filteredDaily.map(d => {
    cum += d.pnl;
    return {
      date: fmtDate(d.date),
      PnL: convert(d.pnl),
      'PnL Cumulé': Math.round(convert(cum) * 100) / 100,
      Trades: d.trades,
    };
  });

  const totalCum = chartData.length > 0 ? chartData[chartData.length - 1]['PnL Cumulé'] : 0;
  const cumulativeColor = totalCum >= 0 ? '#22c55e' : '#ef4444';

  const ASSET_COLORS = ['#22c55e', '#3b82f6', '#eab308'];

  return (
    <AppShell>
      <div className="space-y-5 p-4 lg:p-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-xl font-bold text-text-primary">Performance</h1>
            <p className="mt-0.5 text-sm text-text-muted">Analyse détaillée des résultats du bot</p>
          </div>
          <div className="flex items-center gap-3">
            <CurrencyToggle />
            {/* Range selector */}
          <div className="flex items-center rounded-lg border border-border bg-surface p-1 gap-1">
            {RANGE_BTNS.map(btn => (
              <button
                key={btn.value}
                onClick={() => setRange(btn.value)}
                className={`rounded-md px-3 py-1.5 font-display text-xs font-medium transition-colors ${
                  range === btn.value
                    ? 'bg-surface-hover text-text-primary'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-64 w-full" />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Skeleton className="h-48" />
              <Skeleton className="h-48" />
            </div>
          </div>
        ) : !data || data.daily_pnl.length === 0 ? (
          <Card>
            <EmptyState
              icon={BarChart3}
              title="Pas encore de données de performance"
              description="Les graphiques apparaîtront après les premiers trades clôturés"
              className="py-16"
            />
          </Card>
        ) : (
          <>
            {/* PnL Curve */}
            <Card title="Courbe de PnL cumulé" subtitle={`${filteredDaily.length} jours`}
              headerRight={
                <span className={`font-mono text-lg font-bold ${totalCum >= 0 ? 'text-profit' : 'text-loss'}`}>
                  {fmtPnLValue(totalCum)}
                </span>
              }
            >
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="cumGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={cumulativeColor} stopOpacity={0.25} />
                      <stop offset="95%" stopColor={cumulativeColor} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#52525b', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                    axisLine={false}
                    tickLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fill: '#52525b', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={chartFormatter}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="PnL Cumulé"
                    stroke={cumulativeColor}
                    strokeWidth={2.5}
                    fill="url(#cumGrad)"
                    dot={false}
                    activeDot={{ r: 4, fill: cumulativeColor, stroke: '#0a0a0f', strokeWidth: 2 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Card>

            {/* Middle row: Daily bars + Asset bars */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {/* Daily PnL bars */}
              <Card title="PnL Quotidien">
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={chartData} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
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
                        tickFormatter={chartFormatter}
                      />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="PnL" radius={[3, 3, 0, 0]}>
                      {chartData.map((entry, i) => (
                        <Cell key={i} fill={entry['PnL'] >= 0 ? '#22c55e' : '#ef4444'} fillOpacity={0.8} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              {/* Per-asset performance */}
              <Card title="Performance par Asset">
                {data.by_asset.length === 0 ? (
                  <EmptyState icon={BarChart3} title="Aucune donnée" />
                ) : (
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={data.by_asset} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" vertical={false} />
                      <XAxis
                        dataKey="asset"
                        tick={{ fill: '#52525b', fontSize: 11, fontFamily: 'Space Grotesk' }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: '#52525b', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={chartFormatter}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="total_pnl" name="PnL" radius={[4, 4, 0, 0]}>
                        {data.by_asset.map((entry, i) => (
                          <Cell key={i} fill={ASSET_COLORS[i % ASSET_COLORS.length]} fillOpacity={0.85} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Card>
            </div>

            {/* Pattern performance table + best/worst trades */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              {/* Pattern table */}
              <Card title="Performance par pattern" className="lg:col-span-2" noPadding>
                {data.by_pattern.length === 0 ? (
                  <EmptyState icon={BarChart3} title="Aucune donnée de pattern" className="py-8" />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[400px]">
                      <thead>
                        <tr className="border-b border-border">
                          {['Pattern', 'Trades', 'Win Rate', 'Avg R:R', 'PnL'].map(h => (
                            <th key={h} className="px-4 py-2.5 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data.by_pattern.map(p => (
                          <tr key={p.pattern_type} className="border-b border-border/50 hover:bg-surface-hover">
                            <td className="px-4 py-3">
                              <span className="font-mono text-sm font-semibold text-text-primary">
                                {p.pattern_type?.toUpperCase() ?? '—'}
                              </span>
                            </td>
                            <td className="px-4 py-3 font-mono text-sm text-text-secondary">{p.total_trades}</td>
                            <td className="px-4 py-3">
                              <span className={`font-mono text-sm font-medium ${
                                p.win_rate >= 50 ? 'text-profit' : p.win_rate >= 40 ? 'text-warning' : 'text-loss'
                              }`}>
                                {(p.win_rate ?? 0).toFixed(1)}%
                              </span>
                            </td>
                            <td className="px-4 py-3 font-mono text-sm text-text-secondary">
                              {(p.avg_rr ?? 0).toFixed(2)}R
                            </td>
                            <td className={`px-4 py-3 font-mono text-sm font-semibold ${
                              (p.total_pnl ?? 0) >= 0 ? 'text-profit' : 'text-loss'
                            }`}>
                              {fmtPnL(p.total_pnl ?? 0)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>

              {/* Best / Worst trades */}
              <div className="space-y-3">
                <Card title="Trades remarquables">
                  <div className="space-y-3">
                    {data.best_trade ? (
                      <TradeCard trade={data.best_trade} type="best" />
                    ) : (
                      <p className="text-xs text-text-muted">Aucun trade clôturé</p>
                    )}
                    {data.worst_trade && data.worst_trade.id !== data.best_trade?.id && (
                      <TradeCard trade={data.worst_trade} type="worst" />
                    )}
                  </div>
                </Card>

                {/* Asset win rate summary */}
                {data.by_asset.length > 0 && (
                  <Card title="Win rate par asset">
                    <div className="space-y-3">
                      {data.by_asset.map((a, i) => (
                        <div key={a.asset} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="font-display font-medium text-text-secondary">{a.asset}</span>
                            <span className="font-mono text-text-muted">{a.wins}/{a.total_trades} ({a.win_rate.toFixed(1)}%)</span>
                          </div>
                          <div className="h-1.5 overflow-hidden rounded-full bg-surface-hover">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${a.win_rate}%`,
                                backgroundColor: ASSET_COLORS[i % ASSET_COLORS.length],
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
