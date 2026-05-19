"""Test SSL negotiation then PostgreSQL protocol through cloudflared tunnel."""
import socket, ssl, struct, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
raw.settimeout(10)
raw.connect(('127.0.0.1', 5433))

# Send SSLRequest packet (PostgreSQL SSL negotiation)
# SSLRequest code: 80877103 (0x04D2162F)
sslreq = struct.pack('>I', 8) + struct.pack('>I', 80877103)
raw.sendall(sslreq)

# Read response: b'S' (yes, SSL) or b'N' (no, SSL)
resp = raw.recv(1)
print(f'SSL request response: {resp}')

if resp == b'S':
    print('Server accepts SSL - wrapping socket...')
    ssock = ctx.wrap_socket(raw, server_hostname='localhost')
    print('SSL handshake OK!')

    # Now send PostgreSQL startup message
    params = b'user\x00postgres\x00database\x00postgres\x00\x00'
    length = 4 + 4 + len(params)
    msg = struct.pack('>I', length) + struct.pack('>I', 196608) + params
    ssock.sendall(msg)

    time.sleep(1)

    try:
        data = ssock.recv(8192)
        print(f'Received {len(data)} bytes')
        if data:
            msg_type = chr(data[0])
            print(f'Message type: {msg_type}')
            if msg_type == 'R':
                auth_type = struct.unpack('>I', data[5:9])[0]
                auth_names = {0: 'OK', 3: 'cleartext', 5: 'MD5', 10: 'SASL'}
                name = auth_names.get(auth_type, '?')
                print(f'Auth type: {auth_type} ({name})')
                if auth_type == 5:
                    salt = data[9:13]
                    print(f'Salt: {salt.hex()}')
            elif msg_type == 'K':
                print('SUCCESS - ReadyForQuery!')
            elif msg_type == 'E':
                err = data[1:].decode('utf-8', errors='replace')
                print(f'Error response: {err}')
            else:
                print(f'Raw: {data.hex()[:200]}')
    except socket.timeout:
        print('Timeout after SSL')
    except ConnectionResetError:
        print('Connection reset after SSL')

    ssock.close()
elif resp == b'N':
    print('Server does NOT require SSL - trying without SSL...')
    raw.close()
    raw2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw2.settimeout(10)
    raw2.connect(('127.0.0.1', 5433))
    raw2.sendall(msg)
    time.sleep(1)
    data = raw2.recv(8192)
    print(f'Received without SSL: {data[:200]}')
    raw2.close()
else:
    print(f'Unexpected response: {resp}')
    raw.close()
