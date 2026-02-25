import { NextRequest, NextResponse } from "next/server";
import { getSession } from "better-auth/server";
import { getUserRole, getUserById } from "@/lib/auth-roles";

export async function GET(req: NextRequest) {
  try {
    const session = await getSession();
    
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const user = await getUserById(session.user.id);
    const role = await getUserRole(session.user.id);

    return NextResponse.json({
      user: user,
      role: role,
    });
  } catch (error) {
    console.error("Error getting user info:", error);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
