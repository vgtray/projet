'use client';

import { useEffect, useState, useCallback } from 'react';
import Header from '@/components/Header';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import { formatDate, cn } from '@/lib/utils';

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
  news_sentiment: string | null;
  social_sentiment: string | null;
  llm_used: string | null;
  reason: string | null;
}

function ConfidenceBar({ value }: { value: number }) {
  const color =
    value < 40 ? 'bg-loss' : value < 70 ? 'bg-warning' : 'bg-profit';
  const trackColor =
    value < 40 ? 'bg-loss-dim/40' : value < 70 ? 'bg-warning-dim/40' : 'bg-profit-dim/40';

  return (
    <div className="flex items-center gap-2">
      <div className={cn('h-1.5 w-20 overflow-hidden rounded-full', trackColor)}>
        <div
          className={cn('h-full rounded-full animate-fill', color)}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
      <span className="font-mono text-xs text-text-secondary">{value}%</span>
    </div>
  );
}

function sentimentVariant(s: string | null): 'success' | 'danger' | 'neutral' {
  if (s === 'bullish') return 'success';
  if (s === 'bearish') return 'danger';
  return 'neutral';
}

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [validFilter, setValidFilter] = useState<string>('all');
  const [assetFilter, setAssetFilter] = useState<string>('all');
  const [limit, setLimit] = useState<number>(50);

  const fetchSignals = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      params.set('limit', String(limit));
      if (validFilter === 'valid') params.set('valid', 'true');
      if (validFilter === 'invalid') params.set('valid', 'false');
      if (assetFilter !== 'all') params.set('asset', assetFilter);

      const res = await fetch(`/api/signals?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setSignals(data.signals ?? []);
      }
    } catch { /* retry next interval */ }
  }, [validFilter, assetFilter, limit]);

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, 30_000);
    return () => clearInterval(interval);
  }, [fetchSignals]);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-screen-2xl space-y-6 px-4 py-6 lg:px-6">
        {/* Filtres */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={validFilter}
            onChange={(e) => setValidFilter(e.target.value)}
            className="rounded-md border border-border bg-surface px-3 py-2 font-display text-sm text-text-primary outline-none transition-colors focus:border-border-bright"
          >
            <option value="all">Tous</option>
            <option value="valid">Valides uniquement</option>
            <option value="invalid">Invalides uniquement</option>
          </select>

          <select
            value={assetFilter}
            onChange={(e) => setAssetFilter(e.target.value)}
            className="rounded-md border border-border bg-surface px-3 py-2 font-display text-sm text-text-primary outline-none transition-colors focus:border-border-bright"
          >
            <option value="all">Tous assets</option>
            <option value="XAUUSD">XAUUSD</option>
            <option value="US100">US100</option>
          </select>

          <input
            type="number"
            min={1}
            max={200}
            value={limit}
            onChange={(e) => setLimit(Math.min(200, Math.max(1, parseInt(e.target.value) || 50)))}
            placeholder="Limite"
            className="w-24 rounded-md border border-border bg-surface px-3 py-2 font-mono text-sm text-text-primary outline-none transition-colors focus:border-border-bright"
          />
        </div>

        {/* Tableau signaux */}
        <Card title="Signaux LLM">
          {signals.length === 0 ? (
            <p className="py-8 text-center font-display text-sm text-text-muted">
              Aucun signal trouvé
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1400px]">
                <thead>
                  <tr className="border-b border-border-bright">
                    {['Heure', 'Asset', 'Direction', 'Scénario', 'Confiance', 'Valide', 'Confluences', 'Sweep', 'News', 'Social', 'LLM', 'Raison'].map((h) => (
                      <th key={h} className="px-3 py-2 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {signals.map((signal) => {
                    const isLong = signal.direction === 'long';
                    const isNone = signal.direction === 'none';

                    return (
                      <tr key={signal.id} className="border-b border-border transition-colors hover:bg-surface-hover">
                        <td className="px-3 py-3 text-sm text-text-secondary">
                          {formatDate(signal.timestamp)}
                        </td>
                        <td className="px-3 py-3 font-display text-sm font-semibold text-text-primary">
                          {signal.asset}
                        </td>
                        <td className="px-3 py-3">
                          {isNone ? (
                            <Badge variant="neutral">NONE</Badge>
                          ) : (
                            <Badge variant={isLong ? 'success' : 'danger'}>
                              {signal.direction.toUpperCase()}
                            </Badge>
                          )}
                        </td>
                        <td className="px-3 py-3 font-display text-sm capitalize text-text-secondary">
                          {signal.scenario}
                        </td>
                        <td className="px-3 py-3">
                          <ConfidenceBar value={signal.confidence} />
                        </td>
                        <td className="px-3 py-3">
                          <Badge variant={signal.trade_valid ? 'success' : 'danger'}>
                            {signal.trade_valid ? 'VALID' : 'SKIP'}
                          </Badge>
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex flex-wrap gap-1">
                            {signal.confluences_used?.map((c) => (
                              <Badge key={c} variant="info">{c}</Badge>
                            ))}
                          </div>
                        </td>
                        <td className="px-3 py-3 font-mono text-xs text-text-secondary">
                          {signal.sweep_level?.replace('_', ' ') ?? '—'}
                        </td>
                        <td className="px-3 py-3">
                          {signal.news_sentiment ? (
                            <Badge variant={sentimentVariant(signal.news_sentiment)}>
                              {signal.news_sentiment.toUpperCase()}
                            </Badge>
                          ) : '—'}
                        </td>
                        <td className="px-3 py-3">
                          {signal.social_sentiment ? (
                            <Badge variant={sentimentVariant(signal.social_sentiment)}>
                              {signal.social_sentiment.toUpperCase()}
                            </Badge>
                          ) : '—'}
                        </td>
                        <td className="px-3 py-3 font-mono text-xs text-text-muted">
                          {signal.llm_used ?? '—'}
                        </td>
                        <td className="max-w-[200px] truncate px-3 py-3 text-sm text-text-muted" title={signal.reason ?? ''}>
                          {signal.reason ?? '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </main>
    </>
  );
}
