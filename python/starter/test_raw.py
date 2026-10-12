import json, socket, sys

path = sys.argv[1] if len(sys.argv) > 1 else "../../examples/discover.json"
with open(path, "rb") as f:
    body = f.read()
msg = json.loads(body)

headers = [
    "POST /mcp HTTP/1.1",
    "Host: 127.0.0.1:51000",
    "Content-Type: application/json",
    "Accept: application/json, text/event-stream",
    "MCP-Protocol-Version: 2026-07-28",
    "Mcp-Method: " + msg["method"],
]
if msg["method"] == "tools/call":
    headers.append("Mcp-Name: " + msg["params"]["name"])
headers.append("Content-Length: " + str(len(body)))        # bytes of the file as sent

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("127.0.0.1", 51000))
sock.sendall("\r\n".join(headers).encode("ascii") + b"\r\n\r\n" + body)

sock.settimeout(1.0)                 # the server keeps the connection open, so stop on silence
try:
    while True:
        data = sock.recv(4096)
        if not data:
            break
        print(repr(data))
except socket.timeout:
    pass
sock.close()