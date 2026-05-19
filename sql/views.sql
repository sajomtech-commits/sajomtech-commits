-- ============================================================
-- VIEWS: Dashboard queries optimisées
-- ============================================================

-- 1. Positions ouvertes avec infos compte
CREATE OR REPLACE VIEW public.v_open_positions AS
SELECT
    a.id               AS account_id,
    a.instance_name,
    a.login,
    a.server,
    a.balance,
    a.equity,
    t.ticket,
    t.symbol,
    tt.label           AS trade_type,
    t.volume,
    t.open_time,
    t.open_price,
    t.sl,
    t.tp,
    t.profit,
    t.swap,
    t.commission,
    t.magic,
    t.comment,
    t.close_time
FROM public.trades t
JOIN public.mt5_accounts a ON a.id = t.account_id
LEFT JOIN public.trade_types tt ON tt.id = t.type
WHERE t.is_open = true
ORDER BY t.open_time DESC;

-- 2. Résumé par compte
CREATE OR REPLACE VIEW public.v_account_summary AS
SELECT
    a.id               AS account_id,
    a.instance_name,
    a.login,
    a.server,
    a.balance,
    a.equity,
    a.margin,
    a.margin_free,
    a.leverage,
    a.currency,
    COUNT(t.id) FILTER (WHERE t.is_open)     AS open_positions,
    COUNT(t.id) FILTER (WHERE NOT t.is_open) AS closed_trades,
    COALESCE(SUM(t.profit) FILTER (WHERE NOT t.is_open), 0) AS realized_pnl,
    COALESCE(SUM(t.profit) FILTER (WHERE t.is_open), 0)     AS unrealized_pnl,
    COALESCE(SUM(t.profit), 0)                              AS total_pnl,
    COALESCE(MAX(t.profit) FILTER (WHERE NOT t.is_open), 0) AS best_trade,
    COALESCE(MIN(t.profit) FILTER (WHERE NOT t.is_open), 0) AS worst_trade,
    COUNT(t.id) FILTER (WHERE t.profit > 0 AND NOT t.is_open) AS winning_trades,
    COUNT(t.id) FILTER (WHERE t.profit < 0 AND NOT t.is_open) AS losing_trades
FROM public.mt5_accounts a
LEFT JOIN public.trades t ON t.account_id = a.id
GROUP BY a.id, a.instance_name, a.login, a.server, a.balance, a.equity,
         a.margin, a.margin_free, a.leverage, a.currency;

-- 3. Métriques globales (dashboard overview)
CREATE OR REPLACE VIEW public.v_global_metrics AS
SELECT
    COUNT(DISTINCT a.id) FILTER (WHERE a.is_active) AS active_accounts,
    COUNT(DISTINCT a.id)                            AS total_accounts,
    COUNT(t.id) FILTER (WHERE t.is_open)            AS open_positions,
    COUNT(t.id)                                     AS total_trades,
    COALESCE(SUM(t.profit), 0)                      AS total_pnl,
    COALESCE(
        ROUND(
            100.0 * COUNT(t.id) FILTER (WHERE t.profit > 0 AND NOT t.is_open)
            / NULLIF(COUNT(t.id) FILTER (WHERE t.profit IS NOT NULL AND NOT t.is_open), 0),
        2),
    0)                                              AS win_rate_pct,
    COALESCE(MAX(t.profit) FILTER (WHERE NOT t.is_open), 0) AS best_trade,
    COALESCE(MIN(t.profit) FILTER (WHERE NOT t.is_open), 0) AS worst_trade,
    COALESCE(
        AVG(t.profit) FILTER (WHERE t.profit > 0 AND NOT t.is_open),
    0)                                              AS avg_win,
    COALESCE(
        AVG(t.profit) FILTER (WHERE t.profit < 0 AND NOT t.is_open),
    0)                                              AS avg_loss,
    COALESCE(SUM(t.swap), 0)                        AS total_swap,
    COALESCE(SUM(t.commission), 0)                  AS total_commission
FROM public.mt5_accounts a
JOIN public.trades t ON t.account_id = a.id;

-- 4. PnL quotidien par compte
CREATE OR REPLACE VIEW public.v_daily_pnl AS
SELECT
    DATE(t.close_time) AS trade_date,
    a.id               AS account_id,
    a.instance_name,
    COUNT(t.id)        AS trade_count,
    COALESCE(SUM(t.profit), 0)     AS pnl,
    COALESCE(SUM(t.swap), 0)       AS total_swap,
    COALESCE(SUM(t.commission), 0) AS total_commission
FROM public.trades t
JOIN public.mt5_accounts a ON a.id = t.account_id
WHERE t.close_time IS NOT NULL AND NOT t.is_open
GROUP BY DATE(t.close_time), a.id, a.instance_name
ORDER BY trade_date DESC;

-- 5. PnL quotidien global (tous comptes)
CREATE OR REPLACE VIEW public.v_daily_pnl_global AS
SELECT
    trade_date,
    COUNT(DISTINCT account_id) AS active_accounts,
    SUM(trade_count)           AS total_trades,
    SUM(pnl)                   AS total_pnl,
    SUM(total_swap)            AS total_swap,
    SUM(total_commission)      AS total_commission
FROM public.v_daily_pnl
GROUP BY trade_date
ORDER BY trade_date DESC;

-- 6. Stats par symbole (dashboard filtre)
CREATE OR REPLACE VIEW public.v_trade_stats AS
SELECT
    a.id               AS account_id,
    a.instance_name,
    t.symbol,
    COUNT(t.id)        AS total_trades,
    COUNT(t.id) FILTER (WHERE t.is_open)     AS open_count,
    COUNT(t.id) FILTER (WHERE NOT t.is_open) AS closed_count,
    COUNT(t.id) FILTER (WHERE t.profit > 0 AND NOT t.is_open) AS wins,
    COUNT(t.id) FILTER (WHERE t.profit < 0 AND NOT t.is_open) AS losses,
    COALESCE(
        ROUND(
            100.0 * COUNT(t.id) FILTER (WHERE t.profit > 0 AND NOT t.is_open)
            / NULLIF(COUNT(t.id) FILTER (WHERE t.profit IS NOT NULL AND NOT t.is_open), 0),
        2),
    0) AS win_rate_pct,
    COALESCE(SUM(t.profit), 0) AS total_pnl,
    COALESCE(AVG(t.profit) FILTER (WHERE NOT t.is_open), 0) AS avg_pnl,
    COALESCE(MAX(t.profit), 0) AS best_trade,
    COALESCE(MIN(t.profit), 0) AS worst_trade
FROM public.trades t
JOIN public.mt5_accounts a ON a.id = t.account_id
GROUP BY a.id, a.instance_name, t.symbol
ORDER BY a.instance_name, total_pnl DESC;

-- 7. Dernière synchro par instance
CREATE OR REPLACE VIEW public.v_last_sync AS
SELECT DISTINCT ON (sl.instance_name)
    sl.id,
    sl.instance_name,
    a.login,
    sl.status,
    sl.trades_found,
    sl.trades_upserted,
    sl.duration_ms,
    sl.started_at,
    sl.finished_at
FROM public.sync_log sl
LEFT JOIN public.mt5_accounts a ON a.id = sl.account_id
ORDER BY sl.instance_name, sl.started_at DESC;

-- 8. Drawdown historique par compte (approximé)
CREATE OR REPLACE VIEW public.v_drawdown AS
SELECT
    a.id               AS account_id,
    a.instance_name,
    a.balance,
    a.equity,
    (a.equity - a.balance) AS floating_pnl,
    CASE WHEN a.balance > 0
        THEN ROUND(100.0 * (a.equity - a.balance) / a.balance, 2)
        ELSE 0
    END AS drawdown_pct
FROM public.mt5_accounts a
WHERE a.is_active = true;
