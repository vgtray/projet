'use client';

import { useState } from 'react';
import Badge from '@/components/ui/Badge';
import { formatPrice, formatPnL, formatDate } from '@/lib/utils';
import { X } from 'lucide-react';

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
  closed_reason: string | null;
  entry_time: string;
}

interface TradeRowProps {
  trade: Trade;
  onClose?: () => void;
}

const statusVariant = (trade: Trade) => {
  if (trade.status === 'open') return 'info';
  if (trade.closed_reason === 'tp') return 'success';
  if (trade.closed_reason === 'sl') return 'danger';
  return 'neutral';
};

const statusLabel = (trade: Trade) => {
  if (trade.status === 'open') return 'OPEN';
  if (trade.closed_reason === 'tp') return 'TP HIT';
  if (trade.closed_reason === 'sl') return 'SL HIT';
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
      onClose?.();
    } catch {
      setClosing(false);
    }
  }

  return (
    <tr className="border-b border-border transition-colors hover:bg-surface-hover">
      <td className="px-3 py-3 font-display text-sm font-semibold text-text-primary">
        {trade.asset}
      </td>
      <td className="px-3 py-3">
        <Badge variant={isLong ? 'success' : 'danger'}>
          {isLong ? 'LONG' : 'SHORT'}
        </Badge>
      </td>
      <td className="px-3 py-3 font-mono text-sm text-text-primary">
        {formatPrice(trade.entry_price, trade.asset)}
      </td>
      <td className="px-3 py-3 font-mono text-sm text-loss">
        {formatPrice(trade.sl_price, trade.asset)}
      </td>
      <td className="px-3 py-3 font-mono text-sm text-profit">
        {formatPrice(trade.tp_price, trade.asset)}
      </td>
      <td className="px-3 py-3 font-mono text-sm text-text-secondary">
        {trade.lot_size ?? '—'}
      </td>
      <td className={`px-3 py-3 font-mono text-sm font-semibold ${pnl.color}`}>
        {pnl.text}
      </td>
      <td className="px-3 py-3">
        <Badge variant={statusVariant(trade)}>
          {statusLabel(trade)}
        </Badge>
      </td>
      <td className="px-3 py-3 text-sm text-text-secondary">
        {formatDate(trade.entry_time)}
      </td>
      <td className="px-3 py-3">
        {trade.status === 'open' && (
          <button
            onClick={handleClose}
            disabled={closing}
            className="flex items-center gap-1 rounded border border-loss/30 bg-loss-dim/30 px-2.5 py-1 font-display text-xs font-medium text-loss transition-colors hover:bg-loss-dim/60 disabled:opacity-50"
          >
            <X className="h-3 w-3" />
            {closing ? '...' : 'Fermer'}
          </button>
        )}
      </td>
    </tr>
  );
}
