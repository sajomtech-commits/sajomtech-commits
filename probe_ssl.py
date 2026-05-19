"""Try SSL-wrapped PostgreSQL connection through cloudflared tunnel."""
import socket, ssl, struct, sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
raw.settimeout(10)
raw.connect(('127.0.0.1', 5433))

# First test: try SSL handshake
try:
    ssock = ctx.wrap_socket(raw, server_hostname='localhost')
    print("SSL handshake successful!")
    
    # Now send PostgreSQL startup message over SSL
    params = b'user\x00postgres\x00database\x00postgres\x00\x00'
    length = 4 + 4 + len(params)
    msg = struct.pack('>I', length) + struct.pack('>I', 196608) + params
    ssock.sendall(msg)
    
    import time
    time.sleep(1)
    
    try:
        data = ssock.recv(8192)
        print(f'Received {len(data)} bytes')
        msg_type = chr(data[0]) if data else 'NONE'
        print(f'Message type: {msg_type}')
        if msg_type == 'R':
            auth_type = struct.unpack('>I', data[5:9])[0]
            print(f'Auth type: {auth_type}')
        elif msg_type == 'K':
            print('SUCCESS - connection accepted!')
            print(f'Data: {data.hex()[:100]}')
        elif msg_type == 'E':
            err = data[5:].decode('utf-8', errors='replace')
            print(f'Error: {err}')
        else:
            print(f'Raw: {data[:200]}')
    except socket.timeout:
        print('Timeout after SSL handshake')
    except ConnectionResetError:
        print('Connection reset after SSL handshake')
    
    ssock.close()
except ssl.SSLError as e:
    print(f"SSL error: {e}")
    raw.close()
except Exception as e:
    print(f"Error: {e}")
    raw.close()
