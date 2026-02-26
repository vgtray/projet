'use client';

import { useEffect, useState, useCallback } from 'react';
import AdminGuard from '@/components/AdminGuard';
import AppShell from '@/components/AppShell';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonRow } from '@/components/ui/Skeleton';
import SignalRow, { ConfidenceBar } from '@/components/SignalRow';
import { formatDate } from '@/lib/utils';
import { Radio, Filter } from 'lucide-react';

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

function sentimentVariant(s: string | null): 'success' | 'danger' | 'neutral' {
  if (s === 'bullish') return 'success';
  if (s === 'bearish') return 'danger';
  return 'neutral';
}

const SELECT_CLS = 'rounded-lg border border-border bg-surface px-3 py-2 font-display text-sm text-text-primary outline-none transition-colors focus:border-border-bright hover:border-border-bright';

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
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
    } catch { /* retry */ }
    finally { setLoading(false); }
  }, [validFilter, assetFilter, limit]);

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(fetchSignals, 0);
    const interval = setInterval(fetchSignals, 30_000);
    return () => { clearTimeout(timer); clearInterval(interval); };
  }, [fetchSignals]);

  const HEADERS = ['Asset / Heure', 'Direction', 'Scénario', 'Confiance', 'Valide', 'Confluences', 'Sweep', 'Sentiment News', 'Sentiment Social', 'LLM', 'Raison'];

  return (
    <AdminGuard requiredRole="admin">
      <AppShell>
        <div className="space-y-5 p-4 lg:p-6">
          {/* Header */}
          <div>
            <h1 className="font-display text-xl font-bold text-text-primary">Signaux LLM</h1>
            <p className="mt-0.5 text-sm text-text-muted">Historique des décisions du bot</p>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface p-4">
            <div className="flex items-center gap-2 text-text-muted">
              <Filter className="h-4 w-4" />
              <span className="font-display text-sm font-medium">Filtres</span>
            </div>
            <div className="h-4 w-px bg-border" />
            <select value={validFilter} onChange={e => setValidFilter(e.target.value)} className={SELECT_CLS}>
              <option value="all">Tous les signaux</option>
              <option value="valid">Valides uniquement</option>
              <option value="invalid">Invalides uniquement</option>
            </select>
            <select value={assetFilter} onChange={e => setAssetFilter(e.target.value)} className={SELECT_CLS}>
              <option value="all">Tous les assets</option>
              <option value="XAUUSD">XAUUSD (Gold)</option>
              <option value="US100">US100 (Nasdaq)</option>
            </select>
            <div className="flex items-center gap-2">
              <span className="font-display text-sm text-text-muted">Limite :</span>
              <input
                type="number"
                min={1}
                max={200}
                value={limit}
                onChange={e => setLimit(Math.min(200, Math.max(1, parseInt(e.target.value) || 50)))}
                className={`${SELECT_CLS} w-20 text-center`}
              />
            </div>
            {signals.length > 0 && (
              <span className="ml-auto font-display text-sm text-text-muted">
                {signals.length} signal{signals.length > 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Table */}
          <Card noPadding>
            <div className="overflow-x-auto">
              {loading ? (
                <table className="w-full min-w-[1000px]">
                  <thead>
                    <tr className="border-b border-border">
                      {HEADERS.map(h => (
                        <th key={h} className="px-4 py-2.5 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[...Array(5)].map((_, i) => <SkeletonRow key={i} cols={HEADERS.length} />)}
                  </tbody>
                </table>
              ) : signals.length === 0 ? (
                <EmptyState
                  icon={Radio}
                  title="Aucun signal trouvé"
                  description="Modifiez les filtres ou attendez le prochain cycle du bot"
                  className="py-16"
                />
              ) : (
                <table className="w-full min-w-[1000px]">
                  <thead>
                    <tr className="border-b border-border">
                      {HEADERS.map(h => (
                        <th key={h} className="px-4 py-2.5 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {signals.map(signal => {
                      const isLong = signal.direction === 'long';
                      const isNone = signal.direction === 'none';
                      return (
                        <tr key={signal.id} className="group border-b border-border/50 transition-colors hover:bg-surface-hover">
                          <td className="px-4 py-3">
                            <div className="flex flex-col">
                              <span className="font-display text-sm font-semibold text-text-primary">{signal.asset}</span>
                              <span className="font-mono text-xs text-text-muted">{formatDate(signal.timestamp)}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            {isNone ? (
                              <Badge variant="neutral">NONE</Badge>
                            ) : (
                              <Badge variant={isLong ? 'success' : 'danger'}>
                                {isLong ? '▲ LONG' : '▼ SHORT'}
                              </Badge>
                            )}
                          </td>
                          <td className="px-4 py-3 font-display text-sm capitalize text-text-secondary">
                            {signal.scenario}
                          </td>
                          <td className="px-4 py-3">
                            <ConfidenceBar value={signal.confidence} />
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={signal.trade_valid ? 'success' : 'danger'}>
                              {signal.trade_valid ? '✓ VALID' : '✗ SKIP'}
                            </Badge>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1">
                              {signal.confluences_used?.map(c => (
                                <Badge key={c} variant="info">{c.toUpperCase()}</Badge>
                              )) ?? <span className="font-mono text-xs text-text-muted">—</span>}
                            </div>
                          </td>
                          <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                            {signal.sweep_level?.replace(/_/g, ' ') ?? '—'}
                          </td>
                          <td className="px-4 py-3">
                            {signal.news_sentiment ? (
                              <Badge variant={sentimentVariant(signal.news_sentiment)}>
                                {signal.news_sentiment.toUpperCase()}
                              </Badge>
                            ) : <span className="font-mono text-xs text-text-muted">—</span>}
                          </td>
                          <td className="px-4 py-3">
                            {signal.social_sentiment ? (
                              <Badge variant={sentimentVariant(signal.social_sentiment)}>
                                {signal.social_sentiment.toUpperCase()}
                              </Badge>
                            ) : <span className="font-mono text-xs text-text-muted">—</span>}
                          </td>
                          <td className="px-4 py-3 font-mono text-xs text-text-muted">
                            {signal.llm_used ?? '—'}
                          </td>
                          <td className="max-w-[180px] px-4 py-3">
                            <p className="truncate text-xs text-text-muted" title={signal.reason ?? ''}>
                              {signal.reason ?? '—'}
                            </p>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </Card>
        </div>
      </AppShell>
    </AdminGuard>
  );
}
