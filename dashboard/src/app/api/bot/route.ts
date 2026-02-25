import { NextRequest, NextResponse } from 'next/server';
import { getSession } from 'better-auth/server';
import pool from '@/lib/db';
import { getUserRole } from '@/lib/auth-roles';

export async function POST(req: NextRequest) {
  try {
    const session = await getSession();
    
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userRole = await getUserRole(session.user.id);
    
    if (userRole !== 'owner' && userRole !== 'admin') {
      return NextResponse.json({ error: 'Forbidden - Admin or Owner required' }, { status: 403 });
    }

    const body = await req.json();
    const { action, reason } = body;

    if (action !== 'pause' && action !== 'resume') {
      return NextResponse.json(
        { error: 'Action invalide. Utiliser "pause" ou "resume".' },
        { status: 400 }
      );
    }

    const paused = action === 'pause' ? 'true' : 'false';

    if (action === 'pause') {
      await pool.query(
        `INSERT INTO bot_state (key, value, paused_by, pause_reason, updated_at)
         VALUES ('bot_paused', $1, $2, $3, NOW())
         ON CONFLICT (key) DO UPDATE SET value = $1, paused_by = $2, pause_reason = $3, updated_at = NOW()`,
        [paused, session.user.id, reason || null]
      );
    } else {
      await pool.query(
        `INSERT INTO bot_state (key, value, updated_at)
         VALUES ('bot_paused', $1, NOW())
         ON CONFLICT (key) DO UPDATE SET value = $1, paused_by = NULL, pause_reason = NULL, updated_at = NOW()`,
        [paused]
      );
    }

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

export async function GET(req: NextRequest) {
  try {
    const result = await pool.query(
      "SELECT value, paused_by, pause_reason FROM bot_state WHERE key = 'bot_paused'"
    );
    
    const isPaused = result.rows.length > 0 && result.rows[0].value === 'true';
    
    return NextResponse.json({
      running: !isPaused,
      paused: isPaused,
      pausedBy: result.rows[0]?.paused_by || null,
      pauseReason: result.rows[0]?.pause_reason || null,
    });
  } catch (err) {
    console.error('GET /api/bot error:', err);
    return NextResponse.json({ error: 'Erreur' }, { status: 500 });
  }
}
