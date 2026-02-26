'use client';

import { useState } from 'react';
import Badge from '@/components/ui/Badge';
import { formatPrice, formatPnL, formatDate } from '@/lib/utils';
import { X, Loader2 } from 'lucide-react';

interface Trade {
  id: number;
  asset: string;
  direction: string;
  entry_price: number | string;
  sl_price: number | string | null;
  tp_price: number | string | null;
  lot_size: number | string | null;
  pnl: number | string | null;
  status: string;
  closed_reason?: string | null;
  entry_time: string;
}

interface TradeRowProps {
  trade: Trade;
  onClose?: () => void;
}

const statusVariant = (trade: Trade): 'success' | 'danger' | 'warning' | 'info' | 'neutral' => {
  if (trade.status === 'open') return 'info';
  if (trade.closed_reason === 'tp') return 'success';
  if (trade.closed_reason === 'sl') return 'danger';
  if (trade.closed_reason === 'manual') return 'warning';
  return 'neutral';
};

const statusLabel = (trade: Trade) => {
  if (trade.status === 'open') return 'OPEN';
  if (trade.closed_reason === 'tp') return 'TP ✓';
  if (trade.closed_reason === 'sl') return 'SL ✗';
  if (trade.closed_reason === 'manual') return 'MANUEL';
  if (trade.status === 'closed') return 'CLOSED';
  return trade.status.toUpperCase();
};

export default function TradeRow({ trade, onClose }: TradeRowProps) {
  const [closing, setClosing] = useState(false);
  const pnl = formatPnL(trade.pnl);
  const isLong = trade.direction === 'long';

  async function handleClose() {
    if (closing) return;
    setClosing(true);
    try {
      await fetch(`/api/trades/${trade.id}/close`, { method: 'POST' });
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const res = await fetch('/api/trades?status=open');
          if (res.ok) {
            const data = await res.json();
            const stillOpen = (data.trades ?? []).some((t: { id: number }) => t.id === trade.id);
            if (!stillOpen || attempts >= 10) {
              clearInterval(poll);
              onClose?.();
            }
          }
        } catch {
          if (attempts >= 10) {
            clearInterval(poll);
            setClosing(false);
          }
        }
      }, 2000);
    } catch {
      setClosing(false);
    }
  }

  return (
    <tr className="group border-b border-border/50 transition-colors hover:bg-surface-hover">
      {/* Asset */}
      <td className="px-4 py-3">
        <div className="flex flex-col">
          <span className="font-display text-sm font-semibold text-text-primary">{trade.asset}</span>
          <span className="font-mono text-xs text-text-muted">{formatDate(trade.entry_time)}</span>
        </div>
      </td>
      {/* Direction */}
      <td className="px-4 py-3">
        <Badge variant={isLong ? 'success' : 'danger'}>
          {isLong ? '▲ LONG' : '▼ SHORT'}
        </Badge>
      </td>
      {/* Entry */}
      <td className="px-4 py-3 font-mono text-sm text-text-primary">
        {formatPrice(trade.entry_price, trade.asset)}
      </td>
      {/* SL */}
      <td className="px-4 py-3 font-mono text-sm text-loss/80">
        {formatPrice(trade.sl_price, trade.asset)}
      </td>
      {/* TP */}
      <td className="px-4 py-3 font-mono text-sm text-profit/80">
        {formatPrice(trade.tp_price, trade.asset)}
      </td>
      {/* Lot */}
      <td className="px-4 py-3 font-mono text-sm text-text-secondary">
        {trade.lot_size != null ? Number(trade.lot_size).toFixed(2) : '—'}
      </td>
      {/* PnL */}
      <td className="px-4 py-3">
        <span className={`font-mono text-sm font-semibold ${pnl.color}`}>
          {pnl.text}
        </span>
      </td>
      {/* Status */}
      <td className="px-4 py-3">
        <Badge variant={statusVariant(trade)}>{statusLabel(trade)}</Badge>
      </td>
      {/* Action */}
      <td className="px-4 py-3">
        {trade.status === 'open' && (
          <button
            onClick={handleClose}
            disabled={closing}
            className="flex items-center gap-1 rounded-lg border border-loss/30 bg-loss/5 px-2.5 py-1.5 font-display text-xs font-medium text-loss transition-all hover:bg-loss/15 disabled:opacity-50"
          >
            {closing ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <X className="h-3 w-3" />
            )}
            {closing ? 'Fermeture...' : 'Fermer'}
          </button>
        )}
      </td>
    </tr>
  );
}
