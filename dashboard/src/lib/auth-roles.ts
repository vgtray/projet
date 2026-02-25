import pool from "@/lib/db";

export type UserRole = "owner" | "admin" | "user";

export interface UserWithRole {
  id: string;
  email: string;
  name: string | null;
  role: UserRole;
  createdAt: Date;
}

export async function getUserRole(userId: string): Promise<UserRole> {
  try {
    const result = await pool.query(
      "SELECT role FROM user_roles WHERE user_id = $1",
      [userId]
    );
    if (result.rows.length === 0) {
      return "user";
    }
    return result.rows[0].role as UserRole;
  } catch (error) {
    console.error("Error getting user role:", error);
    return "user";
  }
}

export async function getUserById(userId: string): Promise<UserWithRole | null> {
  try {
    const result = await pool.query(
      `SELECT u.id, u.email, u.name, u."createdAt", COALESCE(r.role, 'user') as role
       FROM "users" u
       LEFT JOIN user_roles r ON u.id = r.user_id
       WHERE u.id = $1`,
      [userId]
    );
    if (result.rows.length === 0) {
      return null;
    }
    return result.rows[0] as UserWithRole;
  } catch (error) {
    console.error("Error getting user by id:", error);
    return null;
  }
}

export async function getAllUsers(): Promise<UserWithRole[]> {
  try {
    const result = await pool.query(
      `SELECT u.id, u.email, u.name, u."createdAt", COALESCE(r.role, 'user') as role
       FROM "users" u
       LEFT JOIN user_roles r ON u.id = r.user_id
       ORDER BY u."createdAt" DESC`
    );
    return result.rows as UserWithRole[];
  } catch (error) {
    console.error("Error getting all users:", error);
    return [];
  }
}

export async function setUserRole(userId: string, role: UserRole): Promise<boolean> {
  try {
    await pool.query(
      `INSERT INTO user_roles (user_id, role)
       VALUES ($1, $2)
       ON CONFLICT (user_id) DO UPDATE SET role = $2`,
      [userId, role]
    );
    return true;
  } catch (error) {
    console.error("Error setting user role:", error);
    return false;
  }
}

export function hasPermission(userRole: UserRole, requiredRole: UserRole): boolean {
  const roleHierarchy: Record<UserRole, number> = {
    owner: 3,
    admin: 2,
    user: 1,
  };
  return roleHierarchy[userRole] >= roleHierarchy[requiredRole];
}
