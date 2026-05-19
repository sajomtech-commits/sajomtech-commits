"""Database setup: verify connection, check tables, provide SQL instructions."""
import os, sys, json, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SRV_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc3ODc4NTIwMCwiZXhwIjo0OTM0NDU4ODAwLCJyb2xlIjoic2VydmljZV9yb2xlIn0.iDaEfe4pHMzkeff9Cu8c-YjwDAes5NY75oPD1oVmuIk"
ANON_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc3ODc4NTIwMCwiZXhwIjo0OTM0NDU4ODAwLCJyb2xlIjoiYW5vbiJ9.dSLctp2RLKsNnrcsxhFafEEeyCSxVHPDpntVPoaJXrA"
BASE = "http://supabase.sagetech.vip"
H = {"apikey": SRV_KEY, "Authorization": f"Bearer {SRV_KEY}",
     "User-Agent": UA, "Accept": "application/json"}

TABLES = ["mt5_accounts", "trades", "sync_log", "scan_config",
          "dashboard_metrics", "trade_types"]


def req(method, path, body=None):
    url = f"{BASE}{path}"
    h = dict(H)
    if body:
        h["Content-Type"] = "application/json"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=10)
        return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def step(n, msg):
    print(f"\n[{n}] {msg}")
    print("-" * 50)


def ok(msg):
    print(f"  OK: {msg}")


def fail(msg):
    print(f"  FAIL: {msg}")


def main():
    print("=" * 60)
    print("  SETUP DATABASE — Trade Dashboard Supabase")
    print("=" * 60)
    print()

    # Step 1: Check API connectivity
    step(1, "API connectivity (HTTP + service_role)")
    c, b = req("GET", "/rest/v1/ventes?limit=1")
    if c == 200:
        ok(f"API accessible (HTTP {c})")
    elif c == 403:
        fail(f"API blocked: {b[:100]}")
        sys.exit(1)
    else:
        fail(f"Unexpected: {c} {b[:100]}")
        sys.exit(1)

    # Step 2: Check existing tables
    step(2, "Check existing tables")
    existing = []
    for t in TABLES:
        c, b = req("GET", f"/rest/v1/{t}?limit=1")
        if c == 200:
            existing.append(t)
            ok(f"{t} exists")
        elif c == 404:
            fail(f"{t} missing (will be created)")
        elif c == 403:
            # Table might exist but blocked by RLS
            existing.append(t)
            ok(f"{t} exists (blocked by RLS)")
        else:
            fail(f"{t} -> {c}: {b[:80]}")

    # Step 3: Test write capability
    step(3, "Write test (service_role POST)")
    c, b = req("POST", "/rest/v1/ventes", {"statut": "__test__", "produit": "__cleanup__"})
    if c in (200, 201, 204):
        # Cleanup
        c2, b2 = req("DELETE", "/rest/v1/ventes?statut=eq.__test__")
        ok(f"Write works (POST {c}, DELETE {c2}) - service_role key valid")
    else:
        fail(f"Write failed: {c} {b[:100]}")

    # Step 4: Check if ventes exists (legacy data)
    step(4, "Legacy data (ventes)")
    c, b = req("GET", "/rest/v1/ventes?limit=1")
    if c == 200:
        data = json.loads(b)
        ok(f"ventes table exists with existing data (preserved)")
    else:
        fail(f"ventes check: {c}")

    # Step 4: Check .env configuration
    step(4, "Configuration check")
    env_path = os.path.join(ROOT, "backend", ".env")
    if os.path.isfile(env_path):
        ok(f".env exists at {env_path}")
        with open(env_path) as f:
            content = f.read()
        if "SUPABASE_URL=http://supabase.sagetech.vip" in content:
            ok("SUPABASE_URL = HTTP (correct)")
        else:
            fail("SUPABASE_URL should use HTTP")
        if SRV_KEY in content:
            ok("SUPABASE_SERVICE_ROLE_KEY present")
        if ANON_KEY in content:
            ok("SUPABASE_ANON_KEY present")
    else:
        fail(".env not found")

    # Step 5: Check ventes count
    step(5, "Ventes count")
    c, b = req("GET", "/rest/v1/ventes?select=count")
    if c == 200:
        ok(f"ventes accessible")
        c2, b2 = req("GET", "/rest/v1/ventes?select=id&limit=1&order=id.desc")
        if c2 == 200:
            max_id = json.loads(b2)[0]["id"] if b2 != "[{}]" and b2.strip() else "?"
            ok(f"last id: {max_id}")

    # Step 6: Summary
    step(6, "Summary")
    if len(existing) == len(TABLES):
        print(f"\n  All {len(TABLES)} tables exist. Backend is ready!")
        print("\n  Run: python backend/scan_all.py --dry-run")
        return

    missing = [t for t in TABLES if t not in existing]
    print(f"\n  {len(existing)}/{len(TABLES)} tables exist.")
    print(f"  Missing: {', '.join(missing)}")
    print("""
  These tables must be created via Supabase Studio SQL Editor.
  Open Supabase Studio (via Coolify or direct URL) and run:

  ─── SQL ORDER (sql/ folder) ───
  1. schema.sql       → CREATE TABLES (with IF NOT EXISTS)
  2. indexes.sql      → performance indexes
  3. views.sql        → dashboard views
  4. rls.sql          → row-level security
    
  IMPORTANT: The existing 'ventes' table will NOT be touched.
  All commands use CREATE TABLE IF NOT EXISTS / CREATE OR REPLACE VIEW.
  """)


if __name__ == "__main__":
    main()
