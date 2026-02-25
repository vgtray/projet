type UserRole = "owner" | "admin" | "user";

interface UserRoleBadgeProps {
  role: UserRole;
}

export default function UserRoleBadge({ role }: UserRoleBadgeProps) {
  const styles = {
    owner: "bg-purple-500/20 text-purple-400 border-purple-500/50",
    admin: "bg-blue-500/20 text-blue-400 border-blue-500/50",
    user: "bg-zinc-500/20 text-zinc-400 border-zinc-500/50",
  };

  const labels = {
    owner: "Owner",
    admin: "Admin",
    user: "User",
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[role]}`}
    >
      {labels[role]}
    </span>
  );
}
