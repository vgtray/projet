import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = req.nextUrl;
    const limit = Math.min(parseInt(searchParams.get('limit') || '20'), 200);
    const validFilter = searchParams.get('valid'); // 'true' | 'false' | null (all)
    const asset = searchParams.get('asset'); // 'XAUUSD' | 'US100' | null (all)

    let query = `
      SELECT
        id, asset, timestamp, direction, scenario, confidence,
        entry_price, sl_price, tp_price, rr_ratio,
        confluences_used, sweep_level, news_sentiment, social_sentiment,
        trade_valid, reason, executed, llm_used, created_at
      FROM signals
    `;

    const conditions: string[] = [];
    const params: (string | number | boolean)[] = [];

    if (validFilter === 'true') {
      conditions.push(`trade_valid = true`);
    } else if (validFilter === 'false') {
      conditions.push(`trade_valid = false`);
    }

    if (asset && (asset === 'XAUUSD' || asset === 'US100')) {
      params.push(asset);
      conditions.push(`asset = $${params.length}`);
    }

    if (conditions.length > 0) {
      query += ` WHERE ${conditions.join(' AND ')}`;
    }

    params.push(limit);
    query += ` ORDER BY timestamp DESC LIMIT $${params.length}`;

    const { rows } = await pool.query(query, params);

    return NextResponse.json({ signals: rows });
  } catch (err) {
    console.error('GET /api/signals error:', err);
    return NextResponse.json(
      { error: 'Erreur lors de la récupération des signaux' },
      { status: 500 }
    );
  }
}
