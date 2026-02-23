import Badge from '@/components/ui/Badge';
import { formatDate } from '@/lib/utils';
import { cn } from '@/lib/utils';

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

export default function SignalRow({ signal }: SignalRowProps) {
  const isLong = signal.direction === 'long';
  const isNone = signal.direction === 'none';

  return (
    <tr className="border-b border-border transition-colors hover:bg-surface-hover">
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
      <td className="max-w-[200px] truncate px-3 py-3 text-sm text-text-muted" title={signal.reason ?? ''}>
        {signal.reason ?? '—'}
      </td>
    </tr>
  );
}
