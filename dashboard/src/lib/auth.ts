import { betterAuth } from "better-auth";
import { Pool } from "pg";
import { nextCookies } from "better-auth/next-js";

export const auth = betterAuth({
  database: new Pool({
    host: process.env.DB_HOST || "localhost",
    port: parseInt(process.env.DB_PORT || "5432"),
    database: process.env.DB_NAME || "trade",
    user: process.env.DB_USER || "adam",
    password: process.env.DB_PASSWORD || "",
    max: 5,
  }),
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,
  },
  plugins: [nextCookies()],
  trustedOrigins: process.env.NODE_ENV === "production" 
    ? [process.env.BETTER_AUTH_URL || ""]
    : ["http://localhost:3000"],
});
