import { NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET() {
  try {
    const client = await pool.connect();
    try {
      // Daily PnL series (last 90 days)
      const dailyRes = await client.query(`
        SELECT
          DATE(exit_time AT TIME ZONE 'Europe/Paris') AS date,
          SUM(pnl)::float AS pnl,
          COUNT(*) AS trades,
          SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins
        FROM trades
        WHERE status = 'closed'
          AND exit_time >= NOW() - INTERVAL '90 days'
        GROUP BY DATE(exit_time AT TIME ZONE 'Europe/Paris')
        ORDER BY date ASC
      `);

      // Per-asset stats
      const assetRes = await client.query(`
        SELECT
          asset,
          COUNT(*) AS total_trades,
          SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins,
          SUM(pnl)::float AS total_pnl,
          AVG(pnl)::float AS avg_pnl,
          CASE WHEN COUNT(*) > 0
            THEN (SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*))
            ELSE 0
          END AS win_rate
        FROM trades
        WHERE status = 'closed'
        GROUP BY asset
        ORDER BY total_trades DESC
      `);

      // Per-pattern performance (from performance_stats table)
      const patternRes = await client.query(`
        SELECT
          pattern_type,
          total_trades,
          wins,
          win_rate::float,
          avg_rr::float,
          total_pnl::float
        FROM performance_stats
        ORDER BY total_trades DESC
        LIMIT 20
      `);

      // Best and worst trades
      const bestWorstRes = await client.query(`
        SELECT
          id, asset, direction, entry_price::float, pnl::float,
          closed_reason, entry_time, exit_time
        FROM trades
        WHERE status = 'closed' AND pnl IS NOT NULL
        ORDER BY pnl DESC
        LIMIT 1
      `);

      const worstRes = await client.query(`
        SELECT
          id, asset, direction, entry_price::float, pnl::float,
          closed_reason, entry_time, exit_time
        FROM trades
        WHERE status = 'closed' AND pnl IS NOT NULL
        ORDER BY pnl ASC
        LIMIT 1
      `);

      // Cumulative PnL
      const cumPnL = dailyRes.rows.reduce((acc: number[], row, i) => {
        const prev = i === 0 ? 0 : acc[i - 1];
        acc.push(Math.round((prev + (row.pnl ?? 0)) * 100) / 100);
        return acc;
      }, []);

      const dailyWithCum = dailyRes.rows.map((row, i) => ({
        date: row.date,
        pnl: Math.round((row.pnl ?? 0) * 100) / 100,
        cumPnl: cumPnL[i],
        trades: parseInt(row.trades),
        wins: parseInt(row.wins),
      }));

      return NextResponse.json({
        daily_pnl: dailyWithCum,
        by_asset: assetRes.rows.map(r => ({
          asset: r.asset,
          total_trades: parseInt(r.total_trades),
          wins: parseInt(r.wins),
          total_pnl: Math.round((r.total_pnl ?? 0) * 100) / 100,
          avg_pnl: Math.round((r.avg_pnl ?? 0) * 100) / 100,
          win_rate: Math.round((r.win_rate ?? 0) * 10) / 10,
        })),
        by_pattern: patternRes.rows,
        best_trade: bestWorstRes.rows[0] ?? null,
        worst_trade: worstRes.rows[0] ?? null,
      });
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Performance API error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
