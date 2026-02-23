import { cn } from '@/lib/utils';

interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export default function Card({ title, children, className }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-surface p-5',
        className
      )}
    >
      {title && (
        <h3 className="mb-4 font-display text-sm font-semibold uppercase tracking-wider text-text-secondary">
          {title}
        </h3>
      )}
      {children}
    </div>
  );
}
