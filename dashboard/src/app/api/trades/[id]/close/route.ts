import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const tradeId = parseInt(id);

    if (isNaN(tradeId)) {
      return NextResponse.json({ error: 'ID invalide' }, { status: 400 });
    }

    const { rows } = await pool.query(
      `SELECT id, status FROM trades WHERE id = $1`,
      [tradeId]
    );

    if (rows.length === 0) {
      return NextResponse.json({ error: 'Trade introuvable' }, { status: 404 });
    }

    if (rows[0].status !== 'open') {
      return NextResponse.json(
        { error: 'Ce trade est déjà fermé' },
        { status: 400 }
      );
    }

    await pool.query(
      `INSERT INTO bot_state (key, value, updated_at)
       VALUES ($1, 'pending', NOW())
       ON CONFLICT (key) DO UPDATE SET value = 'pending', updated_at = NOW()`,
      [`close_trade_${tradeId}`]
    );

    return NextResponse.json({ success: true, trade_id: tradeId });
  } catch (err) {
    console.error('POST /api/trades/[id]/close error:', err);
    return NextResponse.json(
      { error: 'Erreur lors de la demande de fermeture' },
      { status: 500 }
    );
  }
}
