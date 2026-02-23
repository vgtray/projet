import { NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET() {
  try {
    const [globalRes, todayRes, perfRes] = await Promise.all([
      pool.query(`
        SELECT
          COUNT(*)::int AS total_trades,
          COUNT(*) FILTER (WHERE pnl > 0)::int AS winning_trades,
          COUNT(*) FILTER (WHERE pnl <= 0 AND status != 'open')::int AS losing_trades,
          COALESCE(SUM(pnl), 0)::numeric AS total_pnl,
          ROUND(
            CASE WHEN COUNT(*) FILTER (WHERE status != 'open') > 0
            THEN (COUNT(*) FILTER (WHERE pnl > 0)::numeric / COUNT(*) FILTER (WHERE status != 'open') * 100)
            ELSE 0 END, 1
          ) AS win_rate,
          ROUND(COALESCE(AVG(
            CASE WHEN status != 'open' AND sl_price IS NOT NULL AND entry_price IS NOT NULL AND sl_price != entry_price
            THEN ABS(exit_price - entry_price) / ABS(sl_price - entry_price)
            ELSE NULL END
          ), 0), 2) AS avg_rr,
          COUNT(*) FILTER (WHERE status = 'open')::int AS open_trades
        FROM trades
      `),

      pool.query(`
        SELECT asset, closed_trades
        FROM daily_trade_counts
        WHERE trade_date = (NOW() AT TIME ZONE 'Europe/Paris')::date
      `),

      pool.query(`
        SELECT pattern_type, asset, total_trades, winning_trades, losing_trades,
               win_rate, avg_rr, total_pnl, last_updated
        FROM performance_stats
        ORDER BY total_trades DESC
      `),
    ]);

    const global = globalRes.rows[0];
    const todayByAsset: Record<string, number> = {};
    for (const row of todayRes.rows) {
      todayByAsset[row.asset] = row.closed_trades;
    }

    return NextResponse.json({
      global: {
        total_trades: global.total_trades,
        winning_trades: global.winning_trades,
        losing_trades: global.losing_trades,
        total_pnl: parseFloat(global.total_pnl),
        win_rate: parseFloat(global.win_rate),
        avg_rr: parseFloat(global.avg_rr),
        open_trades: global.open_trades,
      },
      today: todayByAsset,
      performance_by_pattern: perfRes.rows,
    });
  } catch (err) {
    console.error('GET /api/stats error:', err);
    return NextResponse.json(
      { error: 'Erreur lors de la récupération des statistiques' },
      { status: 500 }
    );
  }
}
