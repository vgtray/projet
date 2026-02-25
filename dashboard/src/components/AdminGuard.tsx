'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

type UserRole = 'owner' | 'admin' | 'user';

interface AdminGuardProps {
  children: React.ReactNode;
  requiredRole?: UserRole;
}

export default function AdminGuard({ children, requiredRole = 'admin' }: AdminGuardProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);

  useEffect(() => {
    async function checkRole() {
      try {
        const res = await fetch('/api/auth/me');
        if (!res.ok) {
          router.push('/login');
          return;
        }
        const data = await res.json();
        
        const roleHierarchy: Record<UserRole, number> = {
          owner: 3,
          admin: 2,
          user: 1,
        };
        
        const userRole = (data.role || 'user') as UserRole;
        if (roleHierarchy[userRole] >= roleHierarchy[requiredRole]) {
          setHasAccess(true);
        } else {
          router.push('/');
        }
      } catch {
        router.push('/login');
      } finally {
        setLoading(false);
      }
    }
    
    checkRole();
  }, [router, requiredRole]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (!hasAccess) {
    return null;
  }

  return <>{children}</>;
}
