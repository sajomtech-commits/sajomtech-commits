"""Connect to Supabase PostgreSQL via cloudflared tunnel on localhost:5433."""
import psycopg2

DB_PASS = "f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9"
URI = f"postgresql://postgres:{DB_PASS}@localhost:5433/postgres"

print(f"Connecting via tunnel: {URI.replace(DB_PASS, '***')}")
conn = psycopg2.connect(URI, connect_timeout=10)
conn.autocommit = True

cur = conn.cursor()
cur.execute("SELECT version();")
ver = cur.fetchone()[0]
print(f"Connected! PostgreSQL version: {ver}")
cur.close()
conn.close()
