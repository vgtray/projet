'use client';

import { useEffect, useState, useCallback } from 'react';
import AppShell from '@/components/AppShell';
import StatsBar from '@/components/StatsBar';
import Card from '@/components/ui/Card';
import TradeRow from '@/components/TradeRow';
import SignalRow from '@/components/SignalRow';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonRow } from '@/components/ui/Skeleton';
import { Briefcase, History, Radio, RefreshCw } from 'lucide-react';

interface Trade {
  id: number;
  asset: string;
  direction: string;
  entry_price: number | string;
  sl_price: number | string | null;
  tp_price: number | string | null;
  lot_size: number | string | null;
  pnl: number | string | null;
  status: string;
  entry_time: string;
}

interface Signal {
  id: number;
  timestamp: string;
  asset: string;
  direction: string;
  scenario: string;
  confidence: number;
  trade_valid: boolean;
  confluences_used: string[] | null;
  sweep_level: string | null;
  reason: string | null;
}

const TRADE_HEADERS = ['Asset / Heure', 'Direction', 'Entry', 'SL', 'TP', 'Lot', 'PnL', 'Status', 'Action'];
const SIGNAL_HEADERS = ['Asset / Heure', 'Direction', 'Scénario', 'Confiance', 'Valide', 'Confluences', 'Sweep', 'Raison'];

function TableHeader({ headers }: { headers: string[] }) {
  return (
    <thead>
      <tr className="border-b border-border">
        {headers.map(h => (
          <th key={h} className="px-4 py-2.5 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">
            {h}
          </th>
        ))}
      </tr>
    </thead>
  );
}

export default function DashboardPage() {
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);
  const [closedTrades, setClosedTrades] = useState<Trade[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loadingOpen, setLoadingOpen] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchOpenTrades = useCallback(async () => {
    try {
      const res = await fetch('/api/trades?status=open');
      if (res.ok) {
        const data = await res.json();
        setOpenTrades(data.trades ?? []);
      }
    } catch { /* retry next interval */ }
    finally { setLoadingOpen(false); }
  }, []);

  const fetchClosedTrades = useCallback(async () => {
    try {
      const res = await fetch('/api/trades?status=closed&limit=25');
      if (res.ok) {
        const data = await res.json();
        setClosedTrades(data.trades ?? []);
      }
    } catch { /* retry next interval */ }
    finally { setLoadingHistory(false); }
  }, []);

  const fetchSignals = useCallback(async () => {
    try {
      const res = await fetch('/api/signals?limit=10');
      if (res.ok) {
        const data = await res.json();
        setSignals(data.signals ?? []);
      }
    } catch { /* retry next interval */ }
  }, []);

  useEffect(() => {
    fetchOpenTrades();
    const interval = setInterval(() => {
      fetchOpenTrades();
      setLastRefresh(new Date());
    }, 10_000);
    return () => clearInterval(interval);
  }, [fetchOpenTrades]);

  useEffect(() => {
    fetchClosedTrades();
    fetchSignals();
    const interval = setInterval(() => {
      fetchClosedTrades();
      fetchSignals();
    }, 30_000);
    return () => clearInterval(interval);
  }, [fetchClosedTrades, fetchSignals]);

  function handleClose() {
    fetchOpenTrades();
    fetchClosedTrades();
  }

  const refreshLabel = lastRefresh.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  return (
    <AppShell>
      <div className="space-y-5 p-4 lg:p-6">
        {/* Page header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-xl font-bold text-text-primary">Dashboard</h1>
            <p className="mt-0.5 text-sm text-text-muted">Vue d&apos;ensemble du bot en temps réel</p>
          </div>
          <div className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5">
            <RefreshCw className="h-3 w-3 text-text-muted" />
            <span className="font-mono text-xs text-text-muted">{refreshLabel}</span>
          </div>
        </div>

        {/* Stats & Charts */}
        <StatsBar />

        {/* Open Trades */}
        <Card
          title="Trades ouverts"
          noPadding
          headerRight={
            openTrades.length > 0 ? (
              <span className="rounded-full bg-info/10 px-2 py-0.5 font-mono text-xs font-medium text-info">
                {openTrades.length}
              </span>
            ) : null
          }
        >
          <div className="overflow-x-auto">
            {loadingOpen ? (
              <table className="w-full min-w-[700px]">
                <TableHeader headers={TRADE_HEADERS} />
                <tbody>
                  <SkeletonRow cols={9} />
                  <SkeletonRow cols={9} />
                </tbody>
              </table>
            ) : openTrades.length === 0 ? (
              <EmptyState
                icon={Briefcase}
                title="Aucun trade ouvert"
                description="Les trades en cours apparaîtront ici"
                className="py-10"
              />
            ) : (
              <table className="w-full min-w-[700px]">
                <TableHeader headers={TRADE_HEADERS} />
                <tbody>
                  {openTrades.map(trade => (
                    <TradeRow key={trade.id} trade={trade} onClose={handleClose} />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>

        {/* Bottom row: History + Signals side by side on large screens */}
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-5">
          {/* Closed trades history (3/5) */}
          <Card
            title="Historique récent"
            subtitle="25 derniers trades"
            noPadding
            className="xl:col-span-3"
          >
            <div className="overflow-x-auto">
              {loadingHistory ? (
                <table className="w-full min-w-[600px]">
                  <TableHeader headers={TRADE_HEADERS} />
                  <tbody>
                    {[...Array(4)].map((_, i) => <SkeletonRow key={i} cols={9} />)}
                  </tbody>
                </table>
              ) : closedTrades.length === 0 ? (
                <EmptyState
                  icon={History}
                  title="Aucun trade dans l'historique"
                  description="Les trades clôturés apparaîtront ici"
                  className="py-10"
                />
              ) : (
                <table className="w-full min-w-[600px]">
                  <TableHeader headers={TRADE_HEADERS} />
                  <tbody>
                    {closedTrades.map(trade => (
                      <TradeRow key={trade.id} trade={trade} />
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </Card>

          {/* Recent signals (2/5) */}
          <Card
            title="Derniers signaux"
            subtitle="10 derniers"
            noPadding
            className="xl:col-span-2"
          >
            <div className="overflow-x-auto">
              {signals.length === 0 ? (
                <EmptyState
                  icon={Radio}
                  title="Aucun signal reçu"
                  description="Les signaux IA apparaîtront ici"
                  className="py-10"
                />
              ) : (
                <table className="w-full min-w-[500px]">
                  <thead>
                    <tr className="border-b border-border">
                      {['Asset', 'Dir.', 'Confiance', 'Valide', 'Confluences'].map(h => (
                        <th key={h} className="px-4 py-2.5 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {signals.map(signal => (
                      <SignalRow key={signal.id} signal={signal} compact />
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
