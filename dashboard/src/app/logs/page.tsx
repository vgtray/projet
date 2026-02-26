'use client';

import AdminGuard from '@/components/AdminGuard';
import AppShell from '@/components/AppShell';
import LogViewer from '@/components/LogViewer';

export default function LogsPage() {
  return (
    <AdminGuard requiredRole="admin">
      <AppShell>
        <div className="space-y-5 p-4 lg:p-6">
          <div>
            <h1 className="font-display text-xl font-bold text-text-primary">Logs</h1>
            <p className="mt-0.5 text-sm text-text-muted">Activité en temps réel du bot</p>
          </div>
          <LogViewer />
        </div>
      </AppShell>
    </AdminGuard>
  );
}
