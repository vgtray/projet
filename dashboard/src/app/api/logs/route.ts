import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = req.nextUrl;
    const lines = Math.min(parseInt(searchParams.get('lines') || '100'), 500);

    const { rows } = await pool.query(`
      SELECT
        to_char(created_at AT TIME ZONE 'Europe/Paris', 'YYYY-MM-DD HH24:MI:SS') as ts,
        level,
        message
      FROM bot_logs
      ORDER BY created_at DESC
      LIMIT $1
    `, [lines]);

    const logs = rows.reverse().map(r => r.message);

    return NextResponse.json({
      logs,
      total: logs.length,
      returned: logs.length,
    });
  } catch (err) {
    console.error('GET /api/logs error:', err);
    return NextResponse.json({ logs: [], total: 0, returned: 0 });
  }
}
