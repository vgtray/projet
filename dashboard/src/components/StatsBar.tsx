'use client';

import { useEffect, useState } from 'react';
import Card from '@/components/ui/Card';
import {
  BarChart3,
  TrendingUp,
  DollarSign,
  Ratio,
  CircleDot,
  TrendingDown,
} from 'lucide-react';
import { AreaChart, BarChart, DonutChart } from '@tremor/react';

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
  const ddSign = stats.max_drawdown >= 0 ? '-' : '+';

  const chartData = stats.daily_pnl.map(d => ({
    date: formatDate(d.date),
    PnL: d.pnl,
    Trades: d.trades,
  }));

  const assetData = stats.by_asset.map(a => ({
    name: a.asset,
    value: a.total_trades,
    pnl: a.pnl,
  }));

  return (
    <div className="space-y-4">
      {/* KPI Cards */}
      <Card className="p-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-7">
          <div className="flex flex-col">
            <span className="text-xs text-zinc-400 uppercase tracking-wider">Total Trades</span>
            <span className="text-2xl font-bold text-white">{stats.total_trades}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-zinc-400 uppercase tracking-wider">Win Rate</span>
            <span className="text-2xl font-bold text-white">{stats.win_rate.toFixed(1)}%</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-zinc-400 uppercase tracking-wider">Total PnL</span>
            <span className={`text-2xl font-bold ${stats.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {pnlSign}{stats.total_pnl.toFixed(2)} €
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-zinc-400 uppercase tracking-wider">Avg RR</span>
            <span className="text-2xl font-bold text-white">{stats.avg_rr.toFixed(2)}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-zinc-400 uppercase tracking-wider">Max Drawdown</span>
            <span className="text-2xl font-bold text-red-400">{ddSign}{Math.abs(stats.max_drawdown).toFixed(2)} €</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-zinc-400 uppercase tracking-wider">XAUUSD Today</span>
            <span className="text-2xl font-bold text-white">{stats.trades_today_xauusd}/2</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-zinc-400 uppercase tracking-wider">US100 Today</span>
            <span className="text-2xl font-bold text-white">{stats.trades_today_us100}/2</span>
          </div>
        </div>
      </Card>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* PnL Chart */}
        <Card title="PnL Quotidien (30 jours)">
          {chartData.length > 0 ? (
            <AreaChart
              className="h-48 mt-4"
              data={chartData}
              index="date"
              categories={["PnL"]}
              colors={["emerald"]}
              valueFormatter={(v) => `${v >= 0 ? '+' : ''}${v.toFixed(2)} €`}
              showLegend={false}
              showGridLines={false}
            />
          ) : (
            <p className="py-8 text-center text-zinc-400">Aucune donnée</p>
          )}
        </Card>

        {/* Trades by Asset */}
        <Card title="Trades par Asset">
          {assetData.length > 0 ? (
            <div className="h-48 mt-4 flex items-center justify-center">
              <DonutChart
                className="h-40"
                data={assetData}
                category="value"
                index="name"
                colors={["emerald", "blue"]}
                valueFormatter={(v) => `${v} trades`}
                showLabel={true}
              />
            </div>
          ) : (
            <p className="py-8 text-center text-zinc-400">Aucune donnée</p>
          )}
        </Card>
      </div>
    </div>
  );
}
