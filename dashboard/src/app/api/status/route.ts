import { NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET() {
  try {
    const { rows } = await pool.query(`
      SELECT key, value, updated_at
      FROM bot_state
      WHERE key IN ('last_analyzed_XAUUSD', 'last_analyzed_US100', 'bot_paused')
    `);

    const state: Record<string, { value: string; updated_at: string }> = {};
    for (const row of rows) {
      state[row.key] = { value: row.value, updated_at: row.updated_at };
    }

    const now = Date.now();
    const TWO_MIN = 2 * 60 * 1000;

    const lastXAU = state['last_analyzed_XAUUSD']?.value;
    const lastUS = state['last_analyzed_US100']?.value;
    const paused = state['bot_paused']?.value === 'true';

    const xauActive = lastXAU ? (now - new Date(lastXAU).getTime()) < TWO_MIN : false;
    const usActive = lastUS ? (now - new Date(lastUS).getTime()) < TWO_MIN : false;
    const botActive = !paused && (xauActive || usActive);

    return NextResponse.json({
      bot_active: botActive,
      bot_paused: paused,
      last_analyzed_XAUUSD: lastXAU || null,
      last_analyzed_US100: lastUS || null,
      db_connected: true,
    });
  } catch (err) {
    console.error('GET /api/status error:', err);
    return NextResponse.json({
      bot_active: false,
      bot_paused: false,
      last_analyzed_XAUUSD: null,
      last_analyzed_US100: null,
      db_connected: false,
      error: 'Erreur connexion DB',
    }, { status: 500 });
  }
}
