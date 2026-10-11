import socket, sys, time

import socket, sys, time


def make_request(request_id):
    body = ('{"jsonrpc":"2.0","id":%d}' % request_id).encode()
    head = (
        b"POST /mcp HTTP/1.1\r\n"
        b"Host: 127.0.0.1:51000\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(body)).encode() + b"\r\n"
        b"\r\n"
    )
    return head + body


data = make_request(1) + make_request(2)
step = int(sys.argv[1]) if len(sys.argv) > 1 else len(data)   # default: one big send

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.connect(("127.0.0.1", 51000))
for i in range(0, len(data), step):
    sock.sendall(data[i:i + step])
    if step < len(data):
        time.sleep(0.02)
sock.close()