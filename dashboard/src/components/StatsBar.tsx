'use client';

import { useEffect, useState } from 'react';
import Stat from '@/components/ui/Stat';
import Card from '@/components/ui/Card';
import {
  BarChart3,
  TrendingUp,
  DollarSign,
  Ratio,
  CircleDot,
} from 'lucide-react';

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
          trades_today_xauusd: data.today?.XAUUSD ?? 0,
          trades_today_us100: data.today?.US100 ?? 0,
        });
      } catch { /* silently retry next interval */ }
    }

    fetchStats();
    const interval = setInterval(fetchStats, 30_000);
    return () => clearInterval(interval);
  }, []);

  const pnlSign = stats.total_pnl >= 0 ? '+' : '';

  return (
    <Card className="p-4">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Stat
          label="Total Trades"
          value={stats.total_trades}
          icon={<BarChart3 className="h-4 w-4" />}
        />
        <Stat
          label="Win Rate"
          value={`${stats.win_rate.toFixed(1)}%`}
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <Stat
          label="Total PnL"
          value={`${pnlSign}${stats.total_pnl.toFixed(2)} €`}
          icon={<DollarSign className="h-4 w-4" />}
        />
        <Stat
          label="Avg RR"
          value={stats.avg_rr.toFixed(2)}
          icon={<Ratio className="h-4 w-4" />}
        />
        <Stat
          label="Today XAUUSD"
          value={`${stats.trades_today_xauusd}/2`}
          icon={<CircleDot className="h-4 w-4" />}
        />
        <Stat
          label="Today US100"
          value={`${stats.trades_today_us100}/2`}
          icon={<CircleDot className="h-4 w-4" />}
        />
      </div>
    </Card>
  );
}
