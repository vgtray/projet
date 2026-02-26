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
  reason: string | null;
}

interface SignalRowProps {
  signal: Signal;
  compact?: boolean;
}

export function ConfidenceBar({ value }: { value: number }) {
  const color =
    value < 40 ? 'bg-loss' : value < 70 ? 'bg-warning' : 'bg-profit';
  const trackColor =
    value < 40 ? 'bg-loss/20' : value < 70 ? 'bg-warning/20' : 'bg-profit/20';
  const textColor =
    value < 40 ? 'text-loss' : value < 70 ? 'text-warning' : 'text-profit';

  return (
    <div className="flex items-center gap-2">
      <div className={cn('h-1.5 w-16 overflow-hidden rounded-full', trackColor)}>
        <div
          className={cn('h-full rounded-full animate-fill', color)}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
      <span className={cn('font-mono text-xs font-medium', textColor)}>{value}%</span>
    </div>
  );
}

export default function SignalRow({ signal, compact = false }: SignalRowProps) {
  const isLong = signal.direction === 'long';
  const isNone = signal.direction === 'none';

  /* Compact version: 5 cols for dashboard widget */
  if (compact) {
    return (
      <tr className="group border-b border-border/50 transition-colors hover:bg-surface-hover">
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
              {isLong ? '▲' : '▼'} {signal.direction.toUpperCase()}
            </Badge>
          )}
        </td>
        <td className="px-4 py-3">
          <ConfidenceBar value={signal.confidence} />
        </td>
        <td className="px-4 py-3">
          <Badge variant={signal.trade_valid ? 'success' : 'danger'}>
            {signal.trade_valid ? '✓' : '✗'}
          </Badge>
        </td>
        <td className="px-4 py-3">
          <div className="flex flex-wrap gap-1">
            {Array.isArray(signal.confluences_used) && signal.confluences_used.length > 0
              ? signal.confluences_used.slice(0, 2).map(c => (
                  <Badge key={c} variant="info">{c.toUpperCase()}</Badge>
                ))
              : <span className="font-mono text-xs text-text-muted">—</span>
            }
          </div>
        </td>
      </tr>
    );
  }

  /* Full version: 8 cols for signals page */
  return (
    <tr className="group border-b border-border/50 transition-colors hover:bg-surface-hover">
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
          {Array.isArray(signal.confluences_used) && signal.confluences_used.length > 0
            ? signal.confluences_used.map(c => (
                <Badge key={c} variant="info">{c.toUpperCase()}</Badge>
              ))
            : <span className="font-mono text-xs text-text-muted">—</span>
          }
        </div>
      </td>
      <td className="px-4 py-3 font-mono text-xs text-text-secondary">
        {signal.sweep_level?.replace(/_/g, ' ') ?? '—'}
      </td>
      <td className="max-w-[200px] px-4 py-3">
        <p className="truncate text-xs text-text-muted" title={signal.reason ?? ''}>
          {signal.reason ?? '—'}
        </p>
      </td>
    </tr>
  );
}
