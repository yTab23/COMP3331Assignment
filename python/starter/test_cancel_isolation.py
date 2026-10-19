import json, socket, threading, time
import app_support
from mcp_io import Connection, build_request
from client import read_response

HOST, PORT = "127.0.0.1", 51000
outcome = {}


def request_for(station):
    return app_support.request(1, "tools/call",                         # same id and token again
                               {"name": "analyse_readings",
                                "arguments": {"station_id": station}}, "p1")


def run_b():                                                            # B reads its result to the end
    try:
        sock = socket.create_connection((HOST, PORT))
        try:
            sock.sendall(build_request(request_for("AU02"), HOST, PORT))
            _, final, _ = read_response(Connection(sock), 1, "p1")
        finally:
            sock.close()
        outcome["B"] = json.loads(final["result"]["content"][0]["text"])
    except Exception as exc:
        outcome["B"] = exc


b = threading.Thread(target=run_b)
b.start()

a = socket.create_connection((HOST, PORT))                              # A starts, then is cancelled
a.sendall(build_request(request_for("AU01"), HOST, PORT))
time.sleep(1.3)
a.close()                                                               # cancel A: close its connection

b.join()
print("B:", outcome["B"])
ok = (isinstance(outcome["B"], dict) and outcome["B"]["station_id"] == "AU02"
      and outcome["B"]["mean_temperature_c"] == 13.5)
print("PASS" if ok else "FAIL")