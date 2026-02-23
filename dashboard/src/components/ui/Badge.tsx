import { cn } from '@/lib/utils';

type BadgeVariant = 'success' | 'danger' | 'warning' | 'info' | 'neutral';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  success: 'bg-profit-dim/60 text-profit border-profit/20',
  danger: 'bg-loss-dim/60 text-loss border-loss/20',
  warning: 'bg-warning-dim/60 text-warning border-warning/20',
  info: 'bg-info-dim/60 text-info border-info/20',
  neutral: 'bg-neutral-dim/60 text-text-secondary border-neutral/20',
};

export default function Badge({ variant = 'neutral', children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded border px-2 py-0.5 font-mono text-xs font-medium',
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
