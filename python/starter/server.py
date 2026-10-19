import os
import sys
import threading
import json
import socket
import time
import app_support
import traceback
import select
#from student_tools import Cancelled
from mcp_io import Connection, build_response, sse_event, build_request, encode_chunk, LAST_CHUNK

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "support", "python"))
DATASET_PATH = os.path.join(HERE, "support", "data", "readings.json")

import app_support
from student_tools import (TOOLS, load_dataset, get_reading, get_history,
                           analyse_readings, Cancelled)

QUICK_TOOLS = {"get_reading": get_reading, "get_history": get_history}
ALL_TOOL_NAMES = set(QUICK_TOOLS) | {"analyse_readings"}


# --- The three response shapes I could not verify. Fix them here only. ---


def stream_analysis(sock, body, dataset, analysis_delay):
    request_id = body.get("id")
    token = body.get("params").get("_meta").get("progressToken")
    arguments = body.get("params").get("arguments")

    sock.sendall(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/event-stream\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
    )

    # after the SSE headers have been sent:
    stop = threading.Event()
    done = threading.Event()
    watcher = threading.Thread(target=watch_for_disconnect, args=(sock, stop, done), daemon=True)
    watcher.start()
    steps = []

    def progress(done_steps, total):
        steps.append(done_steps)
        sock.sendall(encode_chunk(sse_event(app_support.progress(token, done_steps, total))))

    try:
        try:
            data = analyse_readings(dataset, arguments, analysis_delay, progress, stop)
            final = app_support.result(request_id, tool_success(data))
        except Cancelled:

            print("analysis cancelled after %d of 8 steps at %.2f" % (len(steps), time.time()), file=sys.stderr)
            return False                          # send nothing more; serve_connection closes
        except (ValueError, ArithmeticError) as exc:
            final = app_support.result(request_id, tool_failure(str(exc)))
        sock.sendall(encode_chunk(sse_event(final)))
        sock.sendall(LAST_CHUNK)
        return True
    finally:
        done.set()                                # stop the watcher before the connection is reused
        watcher.join()



def wants_stream(body):
    if body.get("method") != "tools/call":
        return False
    params = body.get("params")
    if not isinstance(params, dict) or params.get("name") != "analyse_readings":
        return False
    meta = params.get("_meta")
    return isinstance(meta, dict) and "progressToken" in meta

def discover_result():
    # GUESS: check against the reference server's real output
    return {"supportedVersions": [app_support.VERSION],
            "capabilities": {"tools": {}}}


def tool_success(data):
    return {
        "content": [{"type": "text",
                     "text": json.dumps(data, separators=(",", ":"), allow_nan=False)}],
        "isError": False,
    }


def tool_failure(message):
    # Inferred: same content shape with isError true. The worked examples
    # show a success only, so confirm against the reference client.
    return {
        "content": [{"type": "text", "text": message}],
        "isError": True,
    }

def handle_request(headers, body, dataset, analysis_delay):
    """Return (http_status, json_payload_dict). Never touches a socket."""
    request_id = body["id"]              # copied through untouched, whatever its type
    method = body["method"]

    if method == "server/discover":
        return 200, app_support.result(request_id, discover_result())

    if method == "tools/list":
        return 200, app_support.result(request_id, {"tools": TOOLS})

    if method == "tools/call":
        name = body["params"]["name"]
        arguments = body["params"]["arguments"]

        if name not in ALL_TOOL_NAMES:   # reject before running anything
            return 400, app_support.error(request_id, -32602, "Unknown tool: " + name)

        try:
            if name == "analyse_readings":
                # Phase 1 only: no streaming, so progress is a no-op, stop never fires.
                data = analyse_readings(dataset, arguments, analysis_delay,
                                        lambda done, total: None, threading.Event())
            else:
                data = QUICK_TOOLS[name](dataset, arguments)
        except (ValueError, ArithmeticError) as exc:
            # Tool failure: HTTP 200 with a completed result, not a JSON-RPC error
            return 200, app_support.result(request_id, tool_failure(str(exc)))

        return 200, app_support.result(request_id, tool_success(data))

    return 404, app_support.error(request_id, -32601, "Method not found: " + method)


def serve_connection(sock, dataset, analysis_delay):
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)   # send progress promptly
    conn = Connection(sock)
    try:
        while True:
            message = conn.read_message()
            if message is None:                       # client closed cleanly
                break
            headers, body = message
            if wants_stream(body):
                if not stream_analysis(sock, body, dataset, analysis_delay):
                    break                             # the client went away mid-stream
                continue
            status, payload = handle_request(headers, body, dataset, analysis_delay)
            sock.sendall(build_response(status, payload))
    except (ConnectionError, OSError, ValueError) as exc:     # a normal bad or dropped client
        print("connection dropped:", type(exc).__name__, exc, file=sys.stderr)
    except Exception:
        traceback.print_exc()                         # a real bug: show it, but keep serving others
    finally:
        sock.close()

def watch_for_disconnect(sock, stop, done):
    """Set `stop` if the client closes the connection. Never consumes any bytes."""
    while not done.is_set():
        try:
            readable, _, _ = select.select([sock], [], [], 0.05)
            if readable:
                if sock.recv(1, socket.MSG_PEEK) == b"":     # peek: look without taking
                    stop.set()                                # the client closed
                return                # closed, or bytes are waiting: nothing more to watch
        except (OSError, ValueError):
            stop.set()                                        # reset or error: treat as gone
            return


def serve_forever(server, dataset, analysis_delay):
    while True:
        try:
            sock, addr = server.accept()
        except socket.timeout:
            continue
        sock.settimeout(None)
        print("accepted", addr, file=sys.stderr)
        threading.Thread(target=serve_connection,
                         args=(sock, dataset, analysis_delay),
                         daemon=True).start()
def main():
    options = app_support.server_options()
    dataset = load_dataset(DATASET_PATH)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", options.port))
    server.listen(32)
    server.settimeout(0.5)
    print("Listening on 127.0.0.1:%d (Ctrl-C to stop)" % options.port, file=sys.stderr)

    try:
        serve_forever(server, dataset, options.analysis_delay)
    except KeyboardInterrupt:
        print("shutting down", file=sys.stderr)
    finally:
        server.close()

if __name__ == "__main__":
    main()