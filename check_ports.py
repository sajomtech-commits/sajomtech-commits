import socket
for addr in ['176.181.28.95']:
    for port in [22, 3389, 80, 443, 4443, 5432, 8000]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        try:
            r = s.connect_ex((addr, port))
            print(f"{addr}:{port} -> {'OPEN' if r == 0 else 'CLOSED'}")
        except Exception as e:
            print(f"{addr}:{port} -> {e}")
        finally:
            s.close()
