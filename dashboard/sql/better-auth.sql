-- Better Auth Schema for PostgreSQL
-- Run this to create the required tables for authentication

-- Users table
CREATE TABLE IF NOT EXISTS "user" (
    "id" VARCHAR(255) PRIMARY KEY,
    "name" VARCHAR(255),
    "email" VARCHAR(255) UNIQUE NOT NULL,
    "emailVerified" BOOLEAN DEFAULT FALSE,
    "image" VARCHAR(255),
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Sessions table
CREATE TABLE IF NOT EXISTS "session" (
    "id" VARCHAR(255) PRIMARY KEY,
    "expiresAt" TIMESTAMPTZ NOT NULL,
    "token" VARCHAR(255) UNIQUE NOT NULL,
    "createdAt" TIMESTAMPTZ NOT NULL,
    "updatedAt" TIMESTAMPTZ NOT NULL,
    "ipAddress" VARCHAR(255),
    "userAgent" VARCHAR(255),
    "userId" VARCHAR(255) NOT NULL REFERENCES "user"("id") ON DELETE CASCADE
);

-- Accounts table (for OAuth and password)
CREATE TABLE IF NOT EXISTS "account" (
    "id" VARCHAR(255) PRIMARY KEY,
    "accountId" VARCHAR(255) NOT NULL,
    "providerId" VARCHAR(255) NOT NULL,
    "userId" VARCHAR(255) NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
    "accessToken" TEXT,
    "refreshToken" TEXT,
    "idToken" TEXT,
    "accessTokenExpiresAt" TIMESTAMPTZ,
    "refreshTokenExpiresAt" TIMESTAMPTZ,
    "scope" VARCHAR(255),
    "password" VARCHAR(255),
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE("providerId", "accountId")
);

-- Verification table
CREATE TABLE IF NOT EXISTS "verification" (
    "id" VARCHAR(255) PRIMARY KEY,
    "identifier" VARCHAR(255) NOT NULL,
    "value" VARCHAR(255) NOT NULL,
    "expiresAt" TIMESTAMPTZ NOT NULL,
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ NOT NULL
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS "session_userId_idx" ON "session"("userId");
CREATE INDEX IF NOT EXISTS "session_token_idx" ON "session"("token");
CREATE INDEX IF NOT EXISTS "account_userId_idx" ON "account"("userId");
CREATE INDEX IF NOT EXISTS "verification_identifier_idx" ON "verification"("identifier");
