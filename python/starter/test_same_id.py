import json, socket, threading
import app_support
from mcp_io import Connection, build_request
from client import read_response

HOST, PORT = "127.0.0.1", 51000
results = {}


def run(station):
    try:
        request = app_support.request(1, "tools/call",                 # same id 1 and token p1 for both
                                      {"name": "analyse_readings",
                                       "arguments": {"station_id": station}}, "p1")
        seen = []
        sock = socket.create_connection((HOST, PORT))
        try:
            sock.sendall(build_request(request, HOST, PORT))
            status, final, _ = read_response(Connection(sock), 1, "p1",
                                             lambda p: seen.append(p["progress"]))
        finally:
            sock.close()
        results[station] = (status, seen, json.loads(final["result"]["content"][0]["text"]))
    except Exception as exc:
        results[station] = exc


threads = [threading.Thread(target=run, args=(s,)) for s in ("AU01", "AU02")]
for t in threads:
    t.start()
for t in threads:
    t.join()

expected = {"AU01": 23.5, "AU02": 13.5}
for station in ("AU01", "AU02"):
    r = results[station]
    if isinstance(r, Exception):
        print(station, "FAIL", type(r).__name__, r)
        continue
    status, seen, data = r
    ok = (data["station_id"] == station and data["mean_temperature_c"] == expected[station]
          and seen == list(range(1, 9)))
    print(station, status, seen, data, "PASS" if ok else "FAIL")