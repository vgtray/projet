'use client';

import { useEffect, useState, useCallback } from 'react';
import Header from '@/components/Header';
import StatsBar from '@/components/StatsBar';
import Card from '@/components/ui/Card';
import TradeRow from '@/components/TradeRow';
import SignalRow from '@/components/SignalRow';

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

export default function DashboardPage() {
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);
  const [closedTrades, setClosedTrades] = useState<Trade[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);

  const fetchOpenTrades = useCallback(async () => {
    try {
      const res = await fetch('/api/trades?status=open');
      if (res.ok) {
        const data = await res.json();
        setOpenTrades(data.trades ?? []);
      }
    } catch { /* retry next interval */ }
  }, []);

  const fetchClosedTrades = useCallback(async () => {
    try {
      const res = await fetch('/api/trades?status=closed&limit=25');
      if (res.ok) {
        const data = await res.json();
        setClosedTrades(data.trades ?? []);
      }
    } catch { /* retry next interval */ }
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
    const timer = setTimeout(() => {
      fetchOpenTrades();
    }, 0);
    const interval = setInterval(fetchOpenTrades, 10_000);
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [fetchOpenTrades]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchClosedTrades();
      fetchSignals();
    }, 0);
    const interval = setInterval(() => {
      fetchClosedTrades();
      fetchSignals();
    }, 30_000);
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [fetchClosedTrades, fetchSignals]);

  function handleClose() {
    fetchOpenTrades();
    fetchClosedTrades();
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-screen-2xl space-y-6 px-4 py-6 lg:px-6">
        <StatsBar />

        {/* Trades ouverts */}
        <section>
          <Card title="Trades ouverts">
            {openTrades.length === 0 ? (
              <p className="py-8 text-center font-display text-sm text-text-muted">
                Aucun trade ouvert
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[900px]">
                  <thead>
                    <tr className="border-b border-border-bright">
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Asset</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Direction</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Entry</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">SL</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">TP</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Lot</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">PnL</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Status</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Heure</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {openTrades.map((trade) => (
                      <TradeRow key={trade.id} trade={trade} onClose={handleClose} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </section>

        {/* Historique récent */}
        <section>
          <Card title="Historique récent (25 derniers)">
            {closedTrades.length === 0 ? (
              <p className="py-8 text-center font-display text-sm text-text-muted">
                Aucun trade dans l&apos;historique
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[900px]">
                  <thead>
                    <tr className="border-b border-border-bright">
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Asset</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Direction</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Entry</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">SL</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">TP</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Lot</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">PnL</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Status</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Heure</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {closedTrades.map((trade) => (
                      <TradeRow key={trade.id} trade={trade} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </section>

        {/* Derniers signaux */}
        <section>
          <Card title="Derniers signaux (10 derniers)">
            {signals.length === 0 ? (
              <p className="py-8 text-center font-display text-sm text-text-muted">
                Aucun signal reçu
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[1000px]">
                  <thead>
                    <tr className="border-b border-border-bright">
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Heure</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Asset</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Direction</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Scénario</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Confiance</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Valide</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Confluences</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Sweep</th>
                      <th className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">Raison</th>
                    </tr>
                  </thead>
                  <tbody>
                    {signals.map((signal) => (
                      <SignalRow key={signal.id} signal={signal} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </section>
      </main>
    </>
  );
}
