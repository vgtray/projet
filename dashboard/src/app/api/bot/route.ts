import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { action } = body;

    if (action !== 'pause' && action !== 'resume') {
      return NextResponse.json(
        { error: 'Action invalide. Utiliser "pause" ou "resume".' },
        { status: 400 }
      );
    }

    const paused = action === 'pause' ? 'true' : 'false';

    await pool.query(
      `INSERT INTO bot_state (key, value, updated_at)
       VALUES ('bot_paused', $1, NOW())
       ON CONFLICT (key) DO UPDATE SET value = $1, updated_at = NOW()`,
      [paused]
    );

    return NextResponse.json({
      success: true,
      state: action === 'pause' ? 'paused' : 'running',
    });
  } catch (err) {
    console.error('POST /api/bot error:', err);
    return NextResponse.json(
      { error: 'Erreur lors du contrôle du bot' },
      { status: 500 }
    );
  }
}
