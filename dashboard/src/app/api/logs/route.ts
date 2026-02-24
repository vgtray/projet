import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = req.nextUrl;
    const lines = Math.min(parseInt(searchParams.get('lines') || '100'), 500);

    // Try to get recent signals as log lines (most useful proxy for bot activity)
    const { rows } = await pool.query(`
      SELECT
        to_char(created_at AT TIME ZONE 'Europe/Paris', 'YYYY-MM-DD HH24:MI:SS') as ts,
        asset,
        direction,
        confidence,
        trade_valid,
        reason,
        llm_used,
        executed
      FROM signals
      ORDER BY created_at DESC
      LIMIT $1
    `, [lines]);

    const logs = rows.reverse().map(row => {
      const valid = row.trade_valid ? 'VALID' : 'SKIP';
      const executed = row.executed ? ' | EXECUTED' : '';
      const llm = row.llm_used ? ` | LLM: ${row.llm_used}` : '';
      return `${row.ts} [INFO] ${row.asset} — ${row.direction?.toUpperCase()} | confidence: ${row.confidence}% | ${valid}${executed}${llm} | ${row.reason ?? ''}`;
    });

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
