'use client';

import { useEffect, useState } from 'react';
import AdminGuard from '@/components/AdminGuard';
import Header from '@/components/Header';
import Card from '@/components/ui/Card';
import { 
  BarChart3, 
  TrendingUp, 
  DollarSign, 
  Ratio,
  CircleDot,
  Activity,
  Pause,
  Play,
  Users,
  Settings
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

export default function AdminDashboard() {
  const [botStatus, setBotStatus] = useState<BotStatus>({ running: true, paused: false, pausedBy: null, pauseReason: null });
  const [stats, setStats] = useState<Stats>(defaultStats);
  const [loading, setLoading] = useState(false);
  const [reason, setReason] = useState('');

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
      if (res.ok) {
        const data = await res.json();
        setBotStatus(data);
      }
    } catch (e) {
      console.error('Error fetching bot status:', e);
    }
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
    } catch (e) {
      console.error('Error fetching stats:', e);
    }
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
        fetchBotStatus();
        setReason('');
      }
    } catch (e) {
      console.error('Error:', e);
    } finally {
      setLoading(false);
    }
  }

  const pnlSign = stats.total_pnl >= 0 ? '+' : '';

  return (
    <AdminGuard requiredRole="owner">
      <Header />
      <main className="mx-auto max-w-screen-2xl space-y-6 px-4 py-6 lg:px-6">
        {/* Bot Control Panel */}
        <Card title="Contrôle du Bot">
          <div className="flex flex-col lg:flex-row gap-6">
            <div className="flex items-center gap-4">
              <div className={`flex items-center gap-2 ${botStatus.running ? 'text-emerald-400' : 'text-red-400'}`}>
                <Activity className="h-5 w-5" />
                <span className="font-medium">{botStatus.running ? 'En cours' : 'Arrêté'}</span>
              </div>
              {botStatus.paused && botStatus.pauseReason && (
                <div className="text-sm text-zinc-400">
                  Pause: {botStatus.pauseReason}
                </div>
              )}
            </div>
            
            <div className="flex flex-col sm:flex-row gap-3 ml-auto">
              {botStatus.running ? (
                <>
                  <input
                    type="text"
                    placeholder="Raison de la pause..."
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white text-sm w-64"
                  />
                  <button
                    onClick={() => handleBotAction('pause')}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-zinc-700 text-white rounded transition-colors"
                  >
                    <Pause className="h-4 w-4" />
                    Mettre en pause
                  </button>
                </>
              ) : (
                <button
                  onClick={() => handleBotAction('resume')}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-zinc-700 text-white rounded transition-colors"
                >
                  <Play className="h-4 w-4" />
                  Reprendre
                </button>
              )}
            </div>
          </div>
        </Card>

        {/* Stats */}
        <Card className="p-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
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
              <span className="text-xs text-zinc-400 uppercase tracking-wider">XAUUSD Today</span>
              <span className="text-2xl font-bold text-white">{stats.trades_today_xauusd}/2</span>
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-zinc-400 uppercase tracking-wider">US100 Today</span>
              <span className="text-2xl font-bold text-white">{stats.trades_today_us100}/2</span>
            </div>
          </div>
        </Card>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <a
            href="/admin/users"
            className="flex items-center gap-4 p-4 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-lg transition-colors"
          >
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Users className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <h3 className="font-medium text-white">Gestion des Utilisateurs</h3>
              <p className="text-sm text-zinc-400">Gérer les rôles et permissions</p>
            </div>
          </a>
          
          <a
            href="/admin/settings"
            className="flex items-center gap-4 p-4 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-lg transition-colors"
          >
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <Settings className="h-6 w-6 text-purple-400" />
            </div>
            <div>
              <h3 className="font-medium text-white">Paramètres</h3>
              <p className="text-sm text-zinc-400">Configuration du bot</p>
            </div>
          </a>
        </div>
      </main>
    </AdminGuard>
  );
}
