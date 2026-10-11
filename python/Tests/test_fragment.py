import socket, sys, time

request = (
    b"POST /mcp HTTP/1.1\r\n"
    b"Host: 127.0.0.1:51000\r\n"
    b"Content-Type: application/json\r\n"
    b"Content-Length: 24\r\n"
    b"\r\n"
    b'{"jsonrpc":"2.0","id":1}'
)

step = int(sys.argv[1]) if len(sys.argv) > 1 else 5   # bytes per send

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # stop Nagle merging small sends
sock.connect(("127.0.0.1", 51000))
for i in range(0, len(request), step):
    sock.sendall(request[i:i + step])
    time.sleep(0.05)
sock.close()