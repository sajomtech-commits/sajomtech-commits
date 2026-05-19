-- ============================================================
-- SCHEMA: MT5 → Supabase Trade Synchronization
-- Phase 3 — Validée
-- ============================================================

-- 1. MT5 ACCOUNTS
CREATE TABLE IF NOT EXISTS public.mt5_accounts (
    id              BIGSERIAL PRIMARY KEY,
    instance_name   TEXT NOT NULL UNIQUE,
    instance_path   TEXT NOT NULL,
    login           BIGINT NOT NULL,
    server          TEXT NOT NULL DEFAULT '',
    account_name    TEXT NOT NULL DEFAULT '',
    balance         NUMERIC(20, 2) DEFAULT 0,
    equity          NUMERIC(20, 2) DEFAULT 0,
    margin          NUMERIC(20, 2) DEFAULT 0,
    margin_free     NUMERIC(20, 2) DEFAULT 0,
    leverage        INTEGER DEFAULT 0,
    currency        TEXT DEFAULT 'USD',
    is_active       BOOLEAN DEFAULT true,
    last_sync_at    TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- 2. TRADES (open positions + historical)
CREATE TABLE IF NOT EXISTS public.trades (
    id              BIGSERIAL PRIMARY KEY,
    account_id      BIGINT NOT NULL REFERENCES public.mt5_accounts(id) ON DELETE CASCADE,
    ticket          BIGINT NOT NULL,
    symbol          TEXT NOT NULL,
    type            SMALLINT NOT NULL,
    volume          NUMERIC(20, 2) NOT NULL DEFAULT 0,
    open_time       TIMESTAMPTZ NOT NULL,
    close_time      TIMESTAMPTZ,
    open_price      NUMERIC(20, 5) NOT NULL DEFAULT 0,
    close_price     NUMERIC(20, 5),
    sl              NUMERIC(20, 5),
    tp              NUMERIC(20, 5),
    profit          NUMERIC(20, 2),
    swap            NUMERIC(20, 2) DEFAULT 0,
    commission      NUMERIC(20, 2) DEFAULT 0,
    magic           BIGINT DEFAULT 0,
    comment         TEXT DEFAULT '',
    is_open         BOOLEAN NOT NULL DEFAULT true,
    updated_at      TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT uq_trade UNIQUE (account_id, ticket)
);

-- 3. SYNC LOG
CREATE TABLE IF NOT EXISTS public.sync_log (
    id              BIGSERIAL PRIMARY KEY,
    instance_name   TEXT NOT NULL,
    account_id      BIGINT REFERENCES public.mt5_accounts(id) ON DELETE SET NULL,
    status          TEXT NOT NULL CHECK (status IN ('started', 'success', 'error')),
    trades_found    INTEGER DEFAULT 0,
    trades_upserted INTEGER DEFAULT 0,
    error_message   TEXT,
    duration_ms     INTEGER DEFAULT 0,
    started_at      TIMESTAMPTZ DEFAULT now(),
    finished_at     TIMESTAMPTZ
);

-- 4. SCAN CONFIG
CREATE TABLE IF NOT EXISTS public.scan_config (
    id              BIGSERIAL PRIMARY KEY,
    instance_name   TEXT NOT NULL UNIQUE,
    scan_interval_s INTEGER NOT NULL DEFAULT 1800,
    is_enabled      BOOLEAN DEFAULT true,
    last_scan_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- 5. DASHBOARD METRICS CACHE
CREATE TABLE IF NOT EXISTS public.dashboard_metrics (
    id                  BIGSERIAL PRIMARY KEY,
    total_accounts      INTEGER DEFAULT 0,
    active_accounts     INTEGER DEFAULT 0,
    open_positions      INTEGER DEFAULT 0,
    total_trades        INTEGER DEFAULT 0,
    total_profit_loss   NUMERIC(20, 2) DEFAULT 0,
    win_rate            NUMERIC(5, 2) DEFAULT 0,
    best_trade          NUMERIC(20, 2) DEFAULT 0,
    worst_trade         NUMERIC(20, 2) DEFAULT 0,
    avg_win             NUMERIC(20, 2) DEFAULT 0,
    avg_loss            NUMERIC(20, 2) DEFAULT 0,
    current_drawdown    NUMERIC(20, 2) DEFAULT 0,
    max_drawdown        NUMERIC(20, 2) DEFAULT 0,
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- 6. TRADE TYPES LOOKUP
CREATE TABLE IF NOT EXISTS public.trade_types (
    id      SMALLINT PRIMARY KEY,
    name    TEXT NOT NULL,
    label   TEXT NOT NULL
);

INSERT INTO public.trade_types (id, name, label) VALUES
    (0, 'buy',          'Buy'),
    (1, 'sell',         'Sell'),
    (2, 'buy_limit',    'Buy Limit'),
    (3, 'sell_limit',   'Sell Limit'),
    (4, 'buy_stop',     'Buy Stop'),
    (5, 'sell_stop',    'Sell Stop')
ON CONFLICT (id) DO NOTHING;
