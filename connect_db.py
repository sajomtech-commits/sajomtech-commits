"""Try all possible Postgres connection URIs to find the database."""
import psycopg2
import socket

uris = [
    # Direct IPs
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@176.181.28.95:5432/postgres",
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@176.181.28.95:5432/supabase",
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@localhost:5432/postgres",
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@127.0.0.1:5432/postgres",
    # Alternative common ports
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@localhost:5433/postgres",
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@localhost:54321/postgres",
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@localhost:54322/postgres",
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@localhost:15432/postgres",
    # Supabase default
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@localhost:5432/supabase",
    # Try without password
    "postgresql://postgres@localhost:5432/postgres",
]

# First check which ports are open
for port in range(5430, 5440):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    for host in ['127.0.0.1', '176.181.28.95', 'localhost']:
        try:
            if s.connect_ex((host, port)) == 0:
                print(f"PORT OPEN: {host}:{port}")
        except:
            pass
    s.close()

# Try each URI
for uri in uris:
    try:
        conn = psycopg2.connect(uri, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        ver = cur.fetchone()[0]
        cur.close()
        conn.close()
        print(f"CONNECTED: {uri}")
        print(f"  Version: {ver}")
        break
    except Exception as e:
        err = str(e)[:80]
        print(f"FAIL: {uri} => {err}")
