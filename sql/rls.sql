-- ============================================================
-- ROW LEVEL SECURITY
-- anon = lecture seule (dashboard)
-- service_role = full access (backend Python)
-- ============================================================

-- Enable RLS
ALTER TABLE public.mt5_accounts       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trades             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sync_log           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scan_config        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dashboard_metrics  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trade_types        ENABLE ROW LEVEL SECURITY;

-- ─── Anon : SELECT only ───

CREATE POLICY anon_select_mt5_accounts ON public.mt5_accounts
    FOR SELECT USING (true);

CREATE POLICY anon_select_trades ON public.trades
    FOR SELECT USING (true);

CREATE POLICY anon_select_sync_log ON public.sync_log
    FOR SELECT USING (true);

CREATE POLICY anon_select_dashboard_metrics ON public.dashboard_metrics
    FOR SELECT USING (true);

CREATE POLICY anon_select_trade_types ON public.trade_types
    FOR SELECT USING (true);

-- Bloquer les écritures anon
CREATE POLICY anon_no_insert_mt5_accounts ON public.mt5_accounts
    FOR INSERT WITH CHECK (false);

CREATE POLICY anon_no_insert_trades ON public.trades
    FOR INSERT WITH CHECK (false);

CREATE POLICY anon_no_update_trades ON public.trades
    FOR UPDATE USING (false);

CREATE POLICY anon_no_delete_trades ON public.trades
    FOR DELETE USING (false);

CREATE POLICY anon_no_insert_sync_log ON public.sync_log
    FOR INSERT WITH CHECK (false);

CREATE POLICY anon_no_update_sync_log ON public.sync_log
    FOR UPDATE USING (false);

-- ─── Grants ───

GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;

GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO anon;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO service_role;
