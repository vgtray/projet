import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface CardProps {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  headerRight?: ReactNode;
  noPadding?: boolean;
}

export default function Card({ title, subtitle, children, className, headerRight, noPadding }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-surface',
        !noPadding && 'p-5',
        className
      )}
    >
      {(title || headerRight) && (
        <div className={cn(
          'flex items-center justify-between',
          !noPadding ? 'mb-4' : 'px-5 pt-4 pb-4 border-b border-border'
        )}>
          <div>
            <h3 className="font-display text-sm font-semibold uppercase tracking-wider text-text-secondary">
              {title}
            </h3>
            {subtitle && (
              <p className="mt-0.5 text-xs text-text-muted">{subtitle}</p>
            )}
          </div>
          {headerRight && <div>{headerRight}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
