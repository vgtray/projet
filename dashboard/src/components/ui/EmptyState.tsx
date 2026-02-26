import { cn } from '@/lib/utils';
import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  className?: string;
}

export default function EmptyState({ icon: Icon, title, description, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center', className)}>
      {Icon && (
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-surface-hover">
          <Icon className="h-6 w-6 text-text-muted" />
        </div>
      )}
      <p className="font-display text-sm font-medium text-text-secondary">{title}</p>
      {description && (
        <p className="mt-1 text-xs text-text-muted">{description}</p>
      )}
    </div>
  );
}
