#!/usr/bin/env python3
"""Bootstrap: execute SQL, setup backend, run first scan."""

import os
import sys
import subprocess

DB_URI = "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@176.181.28.95:5432/postgres"
ROOT = os.path.dirname(os.path.abspath(__file__))


def step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def exec_sql(filepath):
    import psycopg2
    name = os.path.basename(filepath)
    step(f"Executing SQL: {name}")
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()
    conn = psycopg2.connect(DB_URI)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        print(f"  ✓ {name} executed successfully")
    except Exception as e:
        print(f"  ✗ {name} failed: {e}")
        raise
    finally:
        conn.close()


def setup_backend():
    step("Setting up backend")
    backend = os.path.join(ROOT, "backend")
    venv = os.path.join(backend, "venv")
    if not os.path.isdir(venv):
        subprocess.run([sys.executable, "-m", "venv", venv], check=True)
        print("  ✓ Virtual environment created")
    pip = os.path.join(venv, "Scripts", "pip")
    subprocess.run([pip, "install", "-r", os.path.join(backend, "requirements.txt")], check=True)
    print("  ✓ Dependencies installed")

    # Write .env with actual credentials
    env_path = os.path.join(backend, ".env")
    if not os.path.isfile(env_path):
        instances = [
            {"name": "instance1", "path": "C:\\Program Files\\MT5\\terminal64.exe",
             "login": 52883670, "password": "@Q169FwQ!APVuS", "server": "ICMarketsEU-Demo"},
            {"name": "instance2", "path": "C:\\MT5_Portable\\Demo1\\terminal64.exe",
             "login": 52871686, "password": "&AiYW0foMai!oy", "server": "ICMarketsEU-Demo"},
        ]
        import json
        env_content = f"""SUPABASE_URL=https://supabase.sagetech.vip
SUPABASE_SERVICE_ROLE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc3ODc4NTIwMCwiZXhwIjo0OTM0NDU4ODAwLCJyb2xlIjoic2VydmljZV9yb2xlIn0.iDaEfe4pHMzkeff9Cu8c-YjwDAes5NY75oPD1oVmuIk
SUPABASE_ANON_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc3ODc4NTIwMCwiZXhwIjo0OTM0NDU4ODAwLCJyb2xlIjoic2VydmljZV9yb2xlIn0.iDaEfe4pHMzkeff9Cu8c-YjwDAes5NY75oPD1oVmuIk
SCAN_INTERVAL_S=1800
HISTORY_DAYS=365
LOG_LEVEL=INFO
DRY_RUN=0
MT5_INSTANCES={json.dumps(instances)}
"""
        with open(env_path, "w") as f:
            f.write(env_content)
        print("  ✓ .env file created with credentials")


def run_first_scan():
    step("Running first scan (dry run)")
    backend = os.path.join(ROOT, "backend")
    python = os.path.join(backend, "venv", "Scripts", "python")
    result = subprocess.run(
        [python, "scan_all.py", "--once", "--dry-run"],
        cwd=backend,
        capture_output=True, text=True, timeout=60
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[:500])


if __name__ == "__main__":
    step("MT5 TRADE DASHBOARD — BOOTSTRAP")
    print("DB URI:", DB_URI.replace(os.environ.get("DB_PASS", "f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9"), "***"))

    sql_dir = os.path.join(ROOT, "sql")
    for fname in ["schema.sql", "indexes.sql", "views.sql", "rls.sql"]:
        exec_sql(os.path.join(sql_dir, fname))

    setup_backend()
    run_first_scan()

    step("BOOTSTRAP COMPLETE")
    print("""
Next steps:
  1. cd backend
  2. .\\venv\\Scripts\\Activate.ps1
  3. python scan_all.py --once    (actual scan with MT5)
  4. python scan_all.py           (continuous loop, 30min interval)
    """)
