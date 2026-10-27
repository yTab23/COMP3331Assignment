import socket
from mcp_io import Connection


def try_read(label, raw):
    a, b = socket.socketpair()
    a.sendall(raw)
    a.close()
    try:
        print(label, "->", Connection(b).read_message())
    except Exception as exc:
        print(label, "->", type(exc).__name__ + ":", exc)


base = b"POST /mcp HTTP/1.1\r\nHost: x\r\n"
try_read("both framings",      base + b"Content-Length: 2\r\nTransfer-Encoding: chunked\r\n\r\n{}")
try_read("duplicate length",   base + b"Content-Length: 2\r\nContent-Length: 3\r\n\r\n{}")
try_read("negative length",    base + b"Content-Length: -5\r\n\r\n{}")
try_read("non-numeric length", base + b"Content-Length: abc\r\n\r\n{}")
try_read("good request",       base + b"Content-Length: 2\r\n\r\n{}")