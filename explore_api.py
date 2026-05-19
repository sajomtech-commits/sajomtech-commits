"""Explore Supabase REST API to find SQL execution capabilities."""
import urllib.request
import json

KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc3ODc4NTIwMCwiZXhwIjo0OTM0NDU4ODAwLCJyb2xlIjoic2VydmljZV9yb2xlIn0.iDaEfe4pHMzkeff9Cu8c-YjwDAes5NY75oPD1oVmuIk"
BASE = "https://supabase.sagetech.vip"
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Accept": "application/json"}

def req(method, path, body=None, ct="application/json"):
    url = f"{BASE}{path}"
    h = dict(HEADERS)
    if body:
        h["Content-Type"] = ct
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=10)
        return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]

# 1. Check OpenAPI schema for available tables
print("=== OpenAPI Schema (abridged) ===")
code, body = req("GET", "/rest/v1/")
print(f"Status: {code}")
# Parse JSON from OpenAPI spec
try:
    spec = json.loads(body)
    paths = spec.get("paths", {})
    for p, methods in paths.items():
        print(f"  {p}: {list(methods.keys())}")
except:
    print(f"Raw: {body[:200]}")

# 2. Check if we can access pg_catalog tables
print("\n=== Trying pg_catalog access ===")
for tbl in ["pg_tables", "pg_proc", "pg_views", "pg_stat_user_tables", "tables", "views", "procedures"]:
    for schema in ["", "pg_catalog.", "information_schema."]:
        path = f"/rest/v1/{schema}{tbl}?limit=2"
        code, body = req("GET", path)
        if code == 200:
            print(f"  {path} => {code} {body[:200]}")
            break
        elif code == 404 or code == 406:
            pass
        else:
            print(f"  {path} => {code}")

# 3. Check the ventes table structure
print("\n=== ventes table ===")
code, body = req("GET", "/rest/v1/ventes?limit=2")
print(f"  GET /rest/v1/ventes => {code} {body[:300] if code==200 else body}")

# 4. Try to find any RPC functions
print("\n=== RPC functions ===")
for func in ["pg_query", "exec", "execute_sql", "sql_execute", "run_sql", "exec_sql", "pgtle_exec"]:
    code, body = req("POST", f"/rest/v1/rpc/{func}", {"query": "SELECT 1"})
    if code != 404 and code != 405:
        print(f"  {func} => {code} {body[:200]}")

# 5. Check auth endpoint  
print("\n=== Auth endpoint ===")
code, body = req("GET", "/auth/v1/")
print(f"  /auth/v1/ => {code} {body[:200]}")
