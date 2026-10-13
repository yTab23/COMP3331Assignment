import os
import sys
import threading
import json
import socket
import app_support
from mcp_io import Connection, build_response, sse_event, build_request, encode_chunk, LAST_CHUNK

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "support", "python"))
DATASET_PATH = os.path.join(HERE, "support", "data", "readings.json")

import app_support
from student_tools import (TOOLS, load_dataset, get_reading, get_history,
                           analyse_readings)

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

    stop = threading.Event()

    def progress(done, total):
        event = sse_event(app_support.progress(token, done, total))
        sock.sendall(encode_chunk(event))

    try:
        data = analyse_readings(dataset, arguments, analysis_delay, progress, stop)
        final = app_support.result(request_id, tool_success(data))
    except (ValueError, ArithmeticError) as exc:

        final = app_support.result(request_id, tool_failure(str(exc)))
    sock.sendall(encode_chunk(sse_event(final)))
    sock.sendall(LAST_CHUNK)



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
    conn = Connection(sock)
    try:
        while True:
            message = conn.read_message()
            if message is None:                    # client closed cleanly
                break
            headers, body = message
            if wants_stream(body):
                stream_analysis(sock, body, dataset, analysis_delay)
                continue                       # back to read_message(): the connection stays reusable
            status, payload = handle_request(headers, body, dataset, analysis_delay)
            sock.sendall(build_response(status, payload))
    except (ConnectionError, OSError, ValueError, KeyError) as exc:
        print("connection dropped: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)   # never reuse a failed connection
    finally:
        sock.close()


def main():
    options = app_support.server_options()
    dataset = load_dataset(DATASET_PATH)           # once, at startup

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", options.port))
    server.listen()
    print("Listening on 127.0.0.1:%d" % options.port, file=sys.stderr)

    while True:
        sock, _addr = server.accept()
        print("accepted", _addr, file=sys.stderr)
        serve_connection(sock, dataset, options.analysis_delay)


if __name__ == "__main__":
    main()