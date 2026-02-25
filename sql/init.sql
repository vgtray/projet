-- Schéma PostgreSQL pour le bot de trading SMC/ICT
-- Idempotent : peut être exécuté plusieurs fois sans erreur
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    direction VARCHAR(10),
    scenario VARCHAR(20),
    confidence INTEGER,
    entry_price DECIMAL(12,5),
    sl_price DECIMAL(12,5),
    tp_price DECIMAL(12,5),
    rr_ratio DECIMAL(5,2),
    confluences_used TEXT[],
    sweep_level VARCHAR(20),
    news_sentiment VARCHAR(10),
    social_sentiment VARCHAR(10),
    trade_valid BOOLEAN,
    reason TEXT,
    executed BOOLEAN DEFAULT FALSE,
    llm_used VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_signals_asset_timestamp ON signals(asset, timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_trade_valid ON signals(trade_valid);
CREATE INDEX IF NOT EXISTS idx_signals_recent_dedup ON signals(asset, direction, sweep_level, timestamp);
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    asset VARCHAR(10) NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    direction VARCHAR(10) NOT NULL,
    entry_price DECIMAL(12,5) NOT NULL,
    exit_price DECIMAL(12,5),
    sl_price DECIMAL(12,5),
    tp_price DECIMAL(12,5),
    lot_size DECIMAL(10,5),
    mt5_ticket BIGINT,
    pnl DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'open',
    closed_reason VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trades_signal_id ON trades(signal_id);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_asset_entry ON trades(asset, entry_time);
CREATE TABLE IF NOT EXISTS performance_stats (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL,
    asset VARCHAR(10),
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2),
    avg_rr DECIMAL(5,2),
    total_pnl DECIMAL(15,2),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pattern_type, asset)
);
CREATE INDEX IF NOT EXISTS idx_perf_pattern_asset ON performance_stats(pattern_type, asset);
CREATE TABLE IF NOT EXISTS daily_trade_counts (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    closed_trades INTEGER DEFAULT 0,
    UNIQUE(asset, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_daily_counts ON daily_trade_counts(asset, trade_date);
CREATE TABLE IF NOT EXISTS bot_state (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) UNIQUE NOT NULL,
    value TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO bot_state (key, value) VALUES ('last_analyzed_XAUUSD', '')
ON CONFLICT (key) DO NOTHING;
INSERT INTO bot_state (key, value) VALUES ('last_analyzed_US100', '')
ON CONFLICT (key) DO NOTHING;
CREATE TABLE IF NOT EXISTS bot_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bot_logs_created ON bot_logs(created_at DESC);

-- Better Auth tables (idempotent)
CREATE TABLE IF NOT EXISTS "user" (
    "id" VARCHAR(255) PRIMARY KEY,
    "name" VARCHAR(255),
    "email" VARCHAR(255) UNIQUE NOT NULL,
    "emailVerified" BOOLEAN DEFAULT FALSE,
    "image" VARCHAR(255),
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS "verification" (
    "id" VARCHAR(255) PRIMARY KEY,
    "identifier" VARCHAR(255) NOT NULL,
    "value" VARCHAR(255) NOT NULL,
    "expiresAt" TIMESTAMPTZ NOT NULL,
    "createdAt" TIMESTAMPTZ,
    "updatedAt" TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS "session_userId_idx" ON "session"("userId");
CREATE INDEX IF NOT EXISTS "session_token_idx" ON "session"("token");
CREATE INDEX IF NOT EXISTS "account_userId_idx" ON "account"("userId");
CREATE INDEX IF NOT EXISTS "verification_identifier_idx" ON "verification"("identifier");
