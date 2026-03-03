-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enums
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trade_status') THEN
        CREATE TYPE trade_status AS ENUM ('open', 'closed', 'cancelled', 'failed');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trade_side') THEN
        CREATE TYPE trade_side AS ENUM ('buy', 'sell');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'log_level') THEN
        CREATE TYPE log_level AS ENUM ('debug', 'info', 'warning', 'error', 'critical');
    END IF;
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Tables
CREATE TABLE IF NOT EXISTS watchlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol TEXT NOT NULL UNIQUE,
    exchange TEXT NOT NULL DEFAULT 'coinbase',
    is_pinned BOOLEAN DEFAULT false,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
    score NUMERIC(5,2) CHECK (score >= 0 AND score <= 100),
    rating SMALLINT CHECK (rating >= 1 AND rating <= 10),
    short_target NUMERIC(18,8),
    confidence NUMERIC(5,2) CHECK (confidence >= 0 AND confidence <= 1),
    model_version TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    source_snapshots_link TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT unique_signal_per_bucket UNIQUE (symbol, timestamp)
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id UUID REFERENCES signals(id) ON DELETE SET NULL,
    symbol TEXT NOT NULL,
    side trade_side NOT NULL,
    amount NUMERIC(18,8) NOT NULL,
    entry_price NUMERIC(18,8) NOT NULL,
    exit_price NUMERIC(18,8),
    slippage NUMERIC(5,4) DEFAULT 0,
    fees NUMERIC(18,8) DEFAULT 0,
    status trade_status DEFAULT 'open',
    pnl NUMERIC(18,8),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS live_trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id UUID REFERENCES signals(id) ON DELETE SET NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    side trade_side NOT NULL,
    amount NUMERIC(18,8) NOT NULL,
    price NUMERIC(18,8) NOT NULL,
    status trade_status DEFAULT 'open',
    external_order_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS portfolio (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    balance NUMERIC(18,8) DEFAULT 10000.00,
    equity_curve JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT unique_portfolio_user UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS model_usage (
    day DATE NOT NULL,
    model TEXT NOT NULL,
    used_calls INTEGER DEFAULT 0,
    reserved_calls INTEGER DEFAULT 0,
    PRIMARY KEY (day, model)
);

CREATE TABLE IF NOT EXISTS logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level log_level NOT NULL,
    service TEXT NOT NULL,
    message TEXT NOT NULL,
    context JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_watchlist_symbol ON watchlist(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp ON signals(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_paper_trades_status ON paper_trades(status);
CREATE INDEX IF NOT EXISTS idx_model_usage_day ON model_usage(day);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at);

-- Trigger Function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers
DROP TRIGGER IF EXISTS update_watchlist_updated_at ON watchlist;
CREATE TRIGGER update_watchlist_updated_at BEFORE UPDATE ON watchlist FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

DROP TRIGGER IF EXISTS update_paper_trades_updated_at ON paper_trades;
CREATE TRIGGER update_paper_trades_updated_at BEFORE UPDATE ON paper_trades FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

DROP TRIGGER IF EXISTS update_live_trades_updated_at ON live_trades;
CREATE TRIGGER update_live_trades_updated_at BEFORE UPDATE ON live_trades FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

DROP TRIGGER IF EXISTS update_portfolio_updated_at ON portfolio;
CREATE TRIGGER update_portfolio_updated_at BEFORE UPDATE ON portfolio FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
