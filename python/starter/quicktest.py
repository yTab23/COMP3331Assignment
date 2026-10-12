import socket
from mcp_io import Connection, build_response

a, b = socket.socketpair()
a.sendall(build_response(200, {"jsonrpc": "2.0", "id": 1, "result": {}}))
print(Connection(b).read_message())