import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = req.nextUrl;
    const status = searchParams.get('status') || 'all';
    const limit = Math.min(parseInt(searchParams.get('limit') || '50'), 200);

    let query = `
      SELECT
        t.id, t.signal_id, t.asset, t.entry_time, t.exit_time,
        t.direction, t.entry_price, t.exit_price,
        t.sl_price, t.tp_price, t.lot_size, t.mt5_ticket,
        t.pnl, t.status, t.closed_reason, t.created_at,
        s.confluences_used, s.reason, s.scenario, s.confidence,
        s.sweep_level, s.rr_ratio
      FROM trades t
      LEFT JOIN signals s ON t.signal_id = s.id
    `;

    const params: (string | number)[] = [];

    if (status === 'open') {
      query += ` WHERE t.status = 'open'`;
    } else if (status === 'closed') {
      query += ` WHERE t.status != 'open'`;
    }

    query += ` ORDER BY t.entry_time DESC LIMIT $${params.length + 1}`;
    params.push(limit);

    const { rows } = await pool.query(query, params);

    return NextResponse.json({ trades: rows });
  } catch (err) {
    console.error('GET /api/trades error:', err);
    return NextResponse.json(
      { error: 'Erreur lors de la récupération des trades' },
      { status: 500 }
    );
  }
}
