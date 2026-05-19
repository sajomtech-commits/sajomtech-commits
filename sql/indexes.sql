-- ============================================================
-- INDEXES: Performance — 100k+ trades, filtres dashboard
-- ============================================================

-- Couverture complète des requêtes dashboard

-- trades: recherche par compte
CREATE INDEX IF NOT EXISTS idx_trades_account_id       ON public.trades(account_id);
CREATE INDEX IF NOT EXISTS idx_trades_account_ticket   ON public.trades(account_id, ticket);

-- trades: filtres statut
CREATE INDEX IF NOT EXISTS idx_trades_is_open           ON public.trades(is_open);
CREATE INDEX IF NOT EXISTS idx_trades_account_open      ON public.trades(account_id, is_open);

-- trades: filtres temps
CREATE INDEX IF NOT EXISTS idx_trades_open_time         ON public.trades(open_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_close_time        ON public.trades(close_time DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_trades_account_time      ON public.trades(account_id, open_time DESC);

-- trades: filtres symbole / magic
CREATE INDEX IF NOT EXISTS idx_trades_symbol            ON public.trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_symbol_time       ON public.trades(symbol, open_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_magic             ON public.trades(magic);

-- trades: filtres PnL
CREATE INDEX IF NOT EXISTS idx_trades_profit            ON public.trades(profit);

-- trades: composite pour sync
CREATE INDEX IF NOT EXISTS idx_trades_ticket            ON public.trades(ticket);

-- partial index: positions ouvertes uniquement
CREATE INDEX IF NOT EXISTS idx_trades_open_only         ON public.trades(account_id) WHERE is_open = true;

-- mt5_accounts
CREATE INDEX IF NOT EXISTS idx_mt5_accounts_active      ON public.mt5_accounts(is_active);
CREATE INDEX IF NOT EXISTS idx_mt5_accounts_login       ON public.mt5_accounts(login);

-- sync_log
CREATE INDEX IF NOT EXISTS idx_sync_log_instance        ON public.sync_log(instance_name);
CREATE INDEX IF NOT EXISTS idx_sync_log_status          ON public.sync_log(status);
CREATE INDEX IF NOT EXISTS idx_sync_log_started         ON public.sync_log(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_log_account         ON public.sync_log(account_id);
