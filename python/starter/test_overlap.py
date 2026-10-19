import socket, threading, time
import app_support
from mcp_io import Connection, build_request
from client import read_response

results = []                                   # appended as each call finishes


def call(label, request_id, name, arguments, token):
    start = time.time()
    request = app_support.request(request_id, "tools/call",
                                  {"name": name, "arguments": arguments}, token)
    sock = socket.create_connection(("127.0.0.1", 51000))
    sock.sendall(build_request(request, "127.0.0.1", 51000))
    read_response(Connection(sock), request_id, token)
    results.append((label, round(time.time() - start, 2)))
    sock.close()


slow = threading.Thread(target=call,
                        args=("slow analysis", 1, "analyse_readings", {"station_id": "AU01"}, "p1"))
slow.start()
time.sleep(1.0)                                # let the analysis get going
call("quick reading", 2, "get_reading", {"station_id": "AU01"}, None)
slow.join()

for label, seconds in results:
    print(label, seconds, "s")