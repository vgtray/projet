'use client';

import { useEffect, useState } from 'react';
import AdminGuard from '@/components/AdminGuard';
import Header from '@/components/Header';
import Card from '@/components/ui/Card';
import UserRoleBadge from '@/components/UserRoleBadge';
import { format } from 'date-fns';

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
    } catch (e) {
      console.error('Error:', e);
    } finally {
      setLoading(false);
    }
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
    } catch (e) {
      console.error('Error:', e);
    } finally {
      setUpdating(null);
    }
  }

  if (loading) {
    return (
      <AdminGuard requiredRole="owner">
        <div className="min-h-screen flex items-center justify-center bg-zinc-950">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
        </div>
      </AdminGuard>
    );
  }

  return (
    <AdminGuard requiredRole="owner">
      <Header />
      <main className="mx-auto max-w-screen-2xl space-y-6 px-4 py-6 lg:px-6">
        <Card title="Gestion des Utilisateurs">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-400 uppercase">Utilisateur</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-400 uppercase">Email</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-400 uppercase">Rôle</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-400 uppercase">Créé le</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-zinc-400 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-zinc-800/50">
                    <td className="px-4 py-3">
                      <span className="text-white font-medium">{user.name || '—'}</span>
                    </td>
                    <td className="px-4 py-3 text-zinc-300">{user.email}</td>
                    <td className="px-4 py-3">
                      <UserRoleBadge role={user.role} />
                    </td>
                    <td className="px-4 py-3 text-zinc-400 text-sm">
                      {user.createdAt ? format(new Date(user.createdAt), 'dd/MM/yyyy HH:mm') : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {currentUser?.role === 'owner' && user.role !== 'owner' && (
                        <select
                          value={user.role}
                          onChange={(e) => updateRole(user.id, e.target.value as UserRole)}
                          disabled={updating === user.id}
                          className="px-3 py-1.5 bg-zinc-800 border border-zinc-700 rounded text-white text-sm focus:outline-none focus:border-emerald-500 disabled:opacity-50"
                        >
                          <option value="user">User</option>
                          <option value="admin">Admin</option>
                          <option value="owner">Owner</option>
                        </select>
                      )}
                      {user.role === 'owner' && (
                        <span className="text-xs text-zinc-500">Propriétaire</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {users.length === 0 && (
            <p className="py-8 text-center text-zinc-400">Aucun utilisateur</p>
          )}
        </Card>
      </main>
    </AdminGuard>
  );
}
