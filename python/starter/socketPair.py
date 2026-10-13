import socket
from mcp_io import Connection


def run(label, payload, close=False):
    a, b = socket.socketpair()
    c = Connection(b)
    a.sendall(payload)            # send first
    if close:
        a.close()                 # then close, so the reader sees EOF after the partial data
    try:
        print(label, "->", c.read_chunk())
    except Exception as exc:
        print(label, "->", type(exc).__name__ + ":", exc)


run("good chunk",        b"A\r\n0123456789\r\n")
run("bad terminator",    b"A\r\n0123456789XX")
run("cut off mid-body",  b"A\r\n01234", close=True)