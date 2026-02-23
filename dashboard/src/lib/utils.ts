import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(price: number | string | null, asset: string): string {
  if (price === null || price === undefined) return '—';
  const n = typeof price === 'string' ? parseFloat(price) : price;
  if (isNaN(n)) return '—';
  if (asset === 'XAUUSD') return n.toFixed(2);
  if (asset === 'US100') return n.toFixed(1);
  return n.toFixed(2);
}

export function formatPnL(pnl: number | string | null): { text: string; color: string } {
  if (pnl === null || pnl === undefined) return { text: '—', color: 'text-zinc-500' };
  const n = typeof pnl === 'string' ? parseFloat(pnl) : pnl;
  if (isNaN(n)) return { text: '—', color: 'text-zinc-500' };
  const sign = n >= 0 ? '+' : '';
  return {
    text: `${sign}${n.toFixed(2)} €`,
    color: n > 0 ? 'text-emerald-400' : n < 0 ? 'text-red-400' : 'text-zinc-500',
  };
}

export function formatDate(date: string | Date | null): string {
  if (!date) return '—';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Paris',
  });
}

export function timeAgo(date: string | Date | null): string {
  if (!date) return '—';
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000);

  if (diff < 0) return 'dans le futur';
  if (diff < 60) return `il y a ${diff}s`;
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)}h`;
  if (diff < 604800) return `il y a ${Math.floor(diff / 86400)}j`;
  return formatDate(d);
}
