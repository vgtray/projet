'use client';

import AdminGuard from '@/components/AdminGuard';
import AppShell from '@/components/AppShell';
import Card from '@/components/ui/Card';
import { Clock, DollarSign, BarChart3, TrendingUp, Shield } from 'lucide-react';

interface SettingItem {
  label: string;
  value: string;
  description?: string;
}

const settings: { section: string; icon: React.ReactNode; items: SettingItem[] }[] = [
  {
    section: 'Assets tradés',
    icon: <BarChart3 className="h-4 w-4" />,
    items: [
      { label: 'Gold', value: 'XAUUSD', description: 'Paire Gold/Dollar' },
      { label: 'Nasdaq', value: 'US100', description: 'Indice US100 Cash' },
    ],
  },
  {
    section: 'Session de trading',
    icon: <Clock className="h-4 w-4" />,
    items: [
      { label: 'Session NY', value: '14h30 — 21h00', description: 'Heure Paris (CET/CEST)' },
      { label: 'Timeframe', value: 'M5', description: 'Bougie 5 minutes' },
    ],
  },
  {
    section: 'Gestion du risque',
    icon: <Shield className="h-4 w-4" />,
    items: [
      { label: 'Risque par trade', value: '1%', description: 'Du capital total' },
      { label: 'Max trades / jour / asset', value: '2', description: 'Protection contre le surtrading' },
      { label: 'Fenêtre déduplication', value: '15 min', description: 'Délai minimum entre 2 trades identiques' },
    ],
  },
  {
    section: 'Intelligence artificielle',
    icon: <TrendingUp className="h-4 w-4" />,
    items: [
      { label: 'LLM principal', value: 'Claude (Sonnet)', description: 'Anthropic API' },
      { label: 'LLM fallback', value: 'Groq (Llama 3.3 70B)', description: 'Si timeout > 10s' },
      { label: 'Stratégie', value: 'SMC / ICT', description: 'Smart Money Concepts' },
    ],
  },
];

export default function AdminSettingsPage() {
  return (
    <AdminGuard requiredRole="owner">
      <AppShell>
        <div className="space-y-5 p-4 lg:p-6">
          {/* Header */}
          <div>
            <h1 className="font-display text-xl font-bold text-text-primary">Paramètres</h1>
            <p className="mt-0.5 text-sm text-text-muted">
              Configuration du bot — modifiable via variables d&apos;environnement
            </p>
          </div>

          <div className="rounded-xl border border-warning/20 bg-warning/5 px-4 py-3 flex items-start gap-3">
            <DollarSign className="h-4 w-4 text-warning mt-0.5 shrink-0" />
            <p className="text-sm text-warning/80">
              Ces paramètres sont définis dans le fichier <code className="font-mono text-xs">.env</code> du bot Python.
              Pour les modifier, éditez ce fichier et redémarrez le bot.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {settings.map(({ section, icon, items }) => (
              <Card key={section} title={section} headerRight={
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-surface-hover text-text-muted">
                  {icon}
                </div>
              }>
                <div className="space-y-3">
                  {items.map(({ label, value, description }) => (
                    <div key={label} className="flex items-start justify-between gap-4 rounded-lg border border-border bg-bg px-3 py-2.5">
                      <div>
                        <p className="font-display text-sm font-medium text-text-primary">{label}</p>
                        {description && (
                          <p className="text-xs text-text-muted">{description}</p>
                        )}
                      </div>
                      <span className="shrink-0 rounded-md border border-border bg-surface px-2 py-1 font-mono text-xs font-medium text-text-secondary">
                        {value}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </div>
      </AppShell>
    </AdminGuard>
  );
}
