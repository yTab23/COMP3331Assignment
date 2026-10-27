import json, socket
from mcp_io import Connection

HOST, PORT = "127.0.0.1", 51000
META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}}


def rpc(method, request_id=1):
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method,
                       "params": {"_meta": META}}).encode()


def http(method, body, length=None, extra=b""):
    if length is None:
        length = len(body)
    return (b"POST /mcp HTTP/1.1\r\nHost: 127.0.0.1:51000\r\n"
            b"Content-Type: application/json\r\n"
            b"Accept: application/json, text/event-stream\r\n"
            b"MCP-Protocol-Version: 2026-07-28\r\n"
            b"Mcp-Method: " + method.encode() + b"\r\n" + extra +
            b"Content-Length: " + str(length).encode() + b"\r\n\r\n" + body)


def still_serving():
    s = socket.create_connection((HOST, PORT))
    s.settimeout(3)
    try:
        s.sendall(http("server/discover", rpc("server/discover", 99)))
        conn = Connection(s)
        headers, body = conn.read_message()
        print("   follow-up on a new connection:", conn.start_line, "id", body["id"])
    except Exception as exc:
        print("   follow-up FAILED:", type(exc).__name__, exc)
    finally:
        s.close()


def case(label, raw, eof=False):
    s = socket.create_connection((HOST, PORT))
    s.settimeout(3)
    s.sendall(raw)
    if eof:
        s.shutdown(socket.SHUT_WR)         # we are done sending, so the server sees EOF
    try:
        print(label, "->", repr(s.recv(4096)[:80]))
    except socket.timeout:
        print(label, "-> no reply, server still waiting")
    except ConnectionError:
        print(label, "-> connection reset by the server, no reply")
    s.close()
    still_serving()


def keep_alive_after_unknown_method():
    s = socket.create_connection((HOST, PORT))
    s.settimeout(3)
    conn = Connection(s)
    s.sendall(http("nonsense/method", rpc("nonsense/method", 1)))
    headers, body = conn.read_message()
    print("unknown method ->", conn.start_line, body["error"]["code"])
    s.sendall(http("server/discover", rpc("server/discover", 2)))
    headers, body = conn.read_message()
    print("   same connection, next request:", conn.start_line, "id", body["id"])
    s.close()


keep_alive_after_unknown_method()
case("invalid JSON", http("server/discover", b"{not json"))
case("body shorter than Content-Length", http("server/discover", b"0123456789", length=50), eof=True)
case("both framing headers", http("server/discover", rpc("server/discover"),
                                  extra=b"Transfer-Encoding: chunked\r\n"))
case("Content-Length: abc", http("server/discover", rpc("server/discover"), length="abc"))
case("headers cut off", b"POST /mcp HTTP/1.1\r\nHost: x", eof=True)