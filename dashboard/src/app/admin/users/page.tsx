'use client';

import { useEffect, useState } from 'react';
import AdminGuard from '@/components/AdminGuard';
import AppShell from '@/components/AppShell';
import Card from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';
import { SkeletonRow } from '@/components/ui/Skeleton';
import UserRoleBadge from '@/components/UserRoleBadge';
import { format } from 'date-fns';
import { Users } from 'lucide-react';

type UserRole = 'owner' | 'admin' | 'user';

interface User {
  id: string;
  email: string;
  name: string | null;
  role: UserRole;
  createdAt: string;
}

interface CurrentUser {
  role: UserRole;
}

const SELECT_CLS = 'rounded-lg border border-border bg-bg px-2.5 py-1.5 font-display text-sm text-text-primary outline-none transition-colors focus:border-border-bright disabled:opacity-50';

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      const [usersRes, meRes] = await Promise.all([
        fetch('/api/admin/users'),
        fetch('/api/auth/me'),
      ]);
      if (usersRes.ok) {
        const data = await usersRes.json();
        setUsers(data.users || []);
      }
      if (meRes.ok) {
        const data = await meRes.json();
        setCurrentUser(data);
      }
    } catch { /* retry */ }
    finally { setLoading(false); }
  }

  async function updateRole(userId: string, newRole: UserRole) {
    setUpdating(userId);
    try {
      const res = await fetch('/api/admin/users', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, role: newRole }),
      });
      if (res.ok) {
        setUsers(users.map(u => u.id === userId ? { ...u, role: newRole } : u));
      }
    } catch { /* retry */ }
    finally { setUpdating(null); }
  }

  return (
    <AdminGuard requiredRole="owner">
      <AppShell>
        <div className="space-y-5 p-4 lg:p-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-display text-xl font-bold text-text-primary">Utilisateurs</h1>
              <p className="mt-0.5 text-sm text-text-muted">Gestion des rôles et accès</p>
            </div>
            {!loading && (
              <span className="rounded-full border border-border bg-surface px-3 py-1 font-mono text-xs text-text-muted">
                {users.length} utilisateur{users.length > 1 ? 's' : ''}
              </span>
            )}
          </div>

          <Card noPadding>
            <div className="overflow-x-auto">
              {loading ? (
                <table className="w-full min-w-[500px]">
                  <thead>
                    <tr className="border-b border-border">
                      {['Utilisateur', 'Email', 'Rôle', 'Créé le', 'Actions'].map(h => (
                        <th key={h} className="px-4 py-2.5 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[...Array(3)].map((_, i) => <SkeletonRow key={i} cols={5} />)}
                  </tbody>
                </table>
              ) : users.length === 0 ? (
                <EmptyState
                  icon={Users}
                  title="Aucun utilisateur"
                  description="Les utilisateurs inscrits apparaîtront ici"
                  className="py-12"
                />
              ) : (
                <table className="w-full min-w-[500px]">
                  <thead>
                    <tr className="border-b border-border">
                      {['Utilisateur', 'Email', 'Rôle', 'Créé le', 'Actions'].map(h => (
                        <th key={h} className="px-4 py-2.5 text-left font-display text-xs font-semibold uppercase tracking-wider text-text-muted">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(user => (
                      <tr key={user.id} className="border-b border-border/50 transition-colors hover:bg-surface-hover">
                        <td className="px-4 py-3 font-display text-sm font-medium text-text-primary">
                          {user.name || '—'}
                        </td>
                        <td className="px-4 py-3 font-mono text-sm text-text-secondary">{user.email}</td>
                        <td className="px-4 py-3">
                          <UserRoleBadge role={user.role} />
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-text-muted">
                          {user.createdAt ? format(new Date(user.createdAt), 'dd/MM/yyyy HH:mm') : '—'}
                        </td>
                        <td className="px-4 py-3">
                          {currentUser?.role === 'owner' && user.role !== 'owner' ? (
                            <select
                              value={user.role}
                              onChange={e => updateRole(user.id, e.target.value as UserRole)}
                              disabled={updating === user.id}
                              className={SELECT_CLS}
                            >
                              <option value="user">user</option>
                              <option value="admin">admin</option>
                              <option value="owner">owner</option>
                            </select>
                          ) : user.role === 'owner' ? (
                            <span className="font-display text-xs text-text-muted">Propriétaire</span>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </Card>
        </div>
      </AppShell>
    </AdminGuard>
  );
}
