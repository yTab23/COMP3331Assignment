import os
import socket
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "support", "python"))

import app_support
from app_support import client_options
from mcp_io import Connection, build_request, SSEBuffer
from student_tools import parse_json


def classify(status, response):
    """Turn one received response into the reference client's outcome name."""
    if "error" in response:                       # JSON-RPC error beats the HTTP status
        return "protocol_error"
    result = response.get("result")
    if not isinstance(result, dict) or result.get("resultType") != "complete":
        return "invalid_response"
    if status != 200:
        return "http_error"
    if result.get("isError") is True:
        return "tool_error"
    return "success"

def run_call(host, port, request_id, method, parameters, token=None, on_progress=None):
    try:
        status, response = exchange(host, port, request_id, method, parameters, token, on_progress)
    except (ConnectionError, OSError):
        return "network_error", None, None        # no retry: the outcome is uncertain
    except (ValueError, KeyError):
        return "invalid_response", None, None     # includes an id mismatch or bad JSON
    return classify(status, response), status, response


def read_response(conn, request_id, token, on_progress=None):
    headers = conn.read_head()
    if headers is None:
        raise ConnectionError("server closed the connection without a response")
    status = int(conn.start_line.split(" ", 2)[1])

    if "text/event-stream" in headers.get("content-type", ""):
        sse = SSEBuffer()
        final = None
        while True:
            data = conn.read_chunk()
            if data is None:
                break
            for message in sse.feed(data):
                if final is not None:
                    raise ValueError("data after the final response")
                if "id" in message:                       # the final response
                    if not same_value(message["id"], request_id):
                        raise ValueError("response id does not match request id")
                    final = message
                elif message.get("method") == "notifications/progress":
                    params = message["params"]
                    if not same_value(params.get("progressToken"), token):
                        raise ValueError("progress token does not match")
                    if on_progress:
                        on_progress(params)
                else:
                    raise ValueError("unexpected message in stream")                               # your sorting code, unchanged
        if final is None or sse.buffer:
            raise ConnectionError("stream ended without a complete final response")
    else:                                             # lines up with the outer if
        final = json.loads(conn.read_body(headers).decode("utf-8"))
        if not same_value(final.get("id"), request_id):
            raise ValueError("response id does not match request id")

    return status, final, headers


def exchange(host, port, request_id, method, parameters, token=None, on_progress=None):
    request = app_support.request(request_id, method, parameters, token)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        sock.sendall(build_request(request, host, port))
        conn = Connection(sock)
        status, final, _ = read_response(conn, request_id, token, on_progress)

    return status, final

def same_value(a, b):
    """Equal in value and JSON type: 17 is not "17", and 1 is not True."""
    return type(a) is type(b) and a == b




def main():
    options = client_options()
    next_id = 1

    for line in sys.stdin:
        if not line.strip():
            continue

        try:
            command = parse_json(line)
            op = command["op"]
        except (ValueError, KeyError, TypeError):
            app_support.emit("input_error", message="line must be a JSON object with an op")
            continue

        if op == "wait":
            app_support.emit("idle")                 # each call already finished; real waiting is Phase 3
            continue

        if op == "discover":
            method, params, token = "server/discover", {}, None
        elif op == "list":
            method, params, token = "tools/list", {}, None
        elif op == "call":
            name = command.get("name")
            arguments = command.get("arguments")
            if not isinstance(name, str) or not isinstance(arguments, dict):
                app_support.emit("input_error", message="call needs a string name and an arguments object")
                continue
            method, params = "tools/call", {"name": name, "arguments": arguments}
            token = "p%d" % next_id
        else:
            app_support.emit("input_error", message="unsupported op: %s" % op)   # includes cancel, for now
            continue

        request_id = next_id                         # ids are only used up by accepted requests
        next_id += 1
        on_progress = lambda p: app_support.emit("progress", id=request_id, token=token, params=p)

        app_support.emit("started", id=request_id, method=method, token=token)
        outcome, status, response = run_call(options.host, options.port,
                                     request_id, method, params, token, on_progress)

        fields = {"id": request_id, "outcome": outcome}
        if status is not None:
            fields["http_status"] = status           # only when known
        if response is not None:
            fields["response"] = response            # only when one was received
        app_support.emit("finished", **fields)

    app_support.emit("idle")                         # EOF
    return 0

if __name__ == "__main__":
    sys.exit(main())