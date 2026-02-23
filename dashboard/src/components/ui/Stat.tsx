import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface StatProps {
  label: string;
  value: string | number;
  change?: number | null;
  icon?: React.ReactNode;
  className?: string;
}

export default function Stat({ label, value, change, icon, className }: StatProps) {
  const isPositive = change !== null && change !== undefined && change >= 0;
  const hasChange = change !== null && change !== undefined;

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <span className="font-display text-xs font-medium uppercase tracking-wider text-text-secondary">
        {label}
      </span>
      <div className="flex items-end gap-2">
        {icon && <span className="text-text-muted">{icon}</span>}
        <span className="font-display text-2xl font-bold leading-none text-text-primary">
          {value}
        </span>
        {hasChange && (
          <span
            className={cn(
              'flex items-center gap-0.5 font-mono text-xs font-medium',
              isPositive ? 'text-profit' : 'text-loss'
            )}
          >
            {isPositive ? (
              <TrendingUp className="h-3 w-3" />
            ) : (
              <TrendingDown className="h-3 w-3" />
            )}
            {isPositive ? '+' : ''}
            {change.toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
}
