'use client';

import AdminGuard from '@/components/AdminGuard';
import Header from '@/components/Header';
import Card from '@/components/ui/Card';

export default function AdminSettingsPage() {
  return (
    <AdminGuard requiredRole="owner">
      <Header />
      <main className="mx-auto max-w-screen-2xl space-y-6 px-4 py-6 lg:px-6">
        <Card title="Paramètres">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-white mb-2">Configuration du Bot</h3>
              <p className="text-zinc-400 text-sm">Les paramètres du bot sont configurés via les variables d&apos;environnement.</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-zinc-800/50 rounded-lg">
                <h4 className="font-medium text-white mb-1">Assets</h4>
                <p className="text-zinc-400 text-sm">XAUUSD, US100</p>
              </div>
              <div className="p-4 bg-zinc-800/50 rounded-lg">
                <h4 className="font-medium text-white mb-1">Session NY</h4>
                <p className="text-zinc-400 text-sm">14h30 - 21h00 Paris</p>
              </div>
              <div className="p-4 bg-zinc-800/50 rounded-lg">
                <h4 className="font-medium text-white mb-1">Risque par trade</h4>
                <p className="text-zinc-400 text-sm">1% du capital</p>
              </div>
              <div className="p-4 bg-zinc-800/50 rounded-lg">
                <h4 className="font-medium text-white mb-1">Max trades/jour</h4>
                <p className="text-zinc-400 text-sm">2 par asset</p>
              </div>
            </div>
          </div>
        </Card>
      </main>
    </AdminGuard>
  );
}
