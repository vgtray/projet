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
