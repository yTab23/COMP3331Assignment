import socket

request = (
    b"POST /mcp HTTP/1.1\r\n"
    b"Host: 127.0.0.1:51000\r\n"
    b"Content-Type: application/json\r\n"
    b"Content-Length: 24\r\n"
    b"\r\n"
    b'{"jsonrpc":"2.0","id":1}'
)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("127.0.0.1", 51000))
sock.sendall(request)
print("Sent", len(request), "bytes")