import socket, struct, time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(10)
s.connect(('127.0.0.1', 5433))

params = b'user\x00postgres\x00database\x00postgres\x00\x00'
length = 4 + 4 + len(params)
msg = struct.pack('>I', length) + struct.pack('>I', 196608) + params
s.sendall(msg)

time.sleep(1)

try:
    data = s.recv(8192)
    print(f'Received: {len(data)} bytes')
    print(f'Hex: {data.hex()}')
    
    if len(data) >= 1:
        msg_type = chr(data[0])
        print(f'Message type: {msg_type}')
        if msg_type == 'R':
            auth_type = struct.unpack('>I', data[5:9])[0]
            auth_names = {0: 'OK', 3: 'cleartext', 5: 'MD5', 10: 'SASL'}
            print(f'Auth type: {auth_type} ({auth_names.get(auth_type, "unknown")})')
        elif msg_type == 'E':
            err_text = data[5:].decode('utf-8', errors='replace')
            print(f'Error: {err_text}')
        elif msg_type == 'K':
            print('Connection accepted!')
        else:
            print(f'Raw response: {data[:100]}')
except socket.timeout:
    print('Timeout')
except ConnectionResetError:
    print('Connection reset by server')
    
s.close()
