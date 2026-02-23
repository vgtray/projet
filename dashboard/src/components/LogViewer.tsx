'use client';

import { useEffect, useRef, useState } from 'react';
import Card from '@/components/ui/Card';
import { Trash2, Terminal } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LogLine {
  timestamp: string;
  level: string;
  message: string;
}

function parseLogLine(raw: string): LogLine {
  // Format: "2026-02-23 14:30:00 [INFO] Message here"
  const match = raw.match(/^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s\[(\w+)]\s(.*)$/);
  if (match) {
    return { timestamp: match[1], level: match[2], message: match[3] };
  }
  return { timestamp: '', level: '', message: raw };
}

function levelColor(level: string): string {
  switch (level.toUpperCase()) {
    case 'INFO': return 'text-info';
    case 'WARNING': return 'text-warning';
    case 'ERROR': return 'text-loss';
    case 'DEBUG': return 'text-text-muted';
    default: return 'text-text-secondary';
  }
}

export default function LogViewer() {
  const [lines, setLines] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  useEffect(() => {
    async function fetchLogs() {
      try {
        const res = await fetch('/api/logs');
        if (res.ok) {
          const data = await res.json();
          setLines(data.logs?.slice(-100) ?? []);
        }
      } catch { /* retry next interval */ }
    }

    fetchLogs();
    const interval = setInterval(fetchLogs, 5_000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (autoScrollRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  function handleScroll() {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    autoScrollRef.current = scrollHeight - scrollTop - clientHeight < 40;
  }

  function clearLogs() {
    setLines([]);
    autoScrollRef.current = true;
  }

  return (
    <Card className="flex flex-col p-0">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-profit" />
          <h3 className="font-display text-sm font-semibold uppercase tracking-wider text-text-secondary">
            Logs
          </h3>
          <span className="rounded bg-surface-hover px-1.5 py-0.5 font-mono text-xs text-text-muted">
            {lines.length}
          </span>
        </div>
        <button
          onClick={clearLogs}
          className="flex items-center gap-1.5 rounded border border-border px-2.5 py-1 font-display text-xs text-text-muted transition-colors hover:border-border-bright hover:text-text-secondary"
        >
          <Trash2 className="h-3 w-3" />
          Clear
        </button>
      </div>

      {/* Log content */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="terminal-bg min-h-80 flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed"
      >
        {lines.length === 0 ? (
          <div className="flex h-full items-center justify-center text-text-muted">
            En attente de logs...
          </div>
        ) : (
          lines.map((raw, i) => {
            const log = parseLogLine(raw);
            return (
              <div key={i} className="flex gap-2 py-px">
                {log.timestamp && (
                  <span className="shrink-0 text-text-muted">
                    {log.timestamp}
                  </span>
                )}
                {log.level && (
                  <span className={cn('shrink-0 font-semibold', levelColor(log.level))}>
                    [{log.level}]
                  </span>
                )}
                <span className="text-text-primary/80">
                  {log.message}
                </span>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
