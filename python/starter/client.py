import os
import socket
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "support", "python"))

import app_support
from app_support import client_options
from mcp_io import Connection, build_request
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

def run_call(host, port, request_id, method, parameters, token=None):
    try:
        status, response = exchange(host, port, request_id, method, parameters, token)
    except (ConnectionError, OSError):
        return "network_error", None, None        # no retry: the outcome is uncertain
    except (ValueError, KeyError):
        return "invalid_response", None, None     # includes an id mismatch or bad JSON
    return classify(status, response), status, response

def exchange(host, port, request_id, method, parameters, token=None):
    """One request, one response, on a fresh connection. Returns (http_status, response)."""
    request = app_support.request(request_id, method, parameters, token)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        sock.sendall(build_request(request, host, port))
        conn = Connection(sock)
        message = conn.read_message()

    if message is None:                                   # closed with no response
        raise ConnectionError("server closed the connection without a response")
    headers, response = message

    status = int(conn.start_line.split(" ", 2)[1])        # "HTTP/1.1 200 OK" -> 200

    got = response.get("id")
    if type(got) is not type(request_id) or got != request_id:
        raise ValueError("response id does not match request id")   # never report it as a result
    return status, response


def main():
    options = client_options()
    status, response = exchange(options.host, options.port, 1, "server/discover", {})
    print(status, response)

    print(classify(200, {"result": {"resultType": "complete", "isError": False}}))   # success
    print(classify(200, {"result": {"resultType": "complete", "isError": True}}))    # tool_error
    print(classify(400, {"error": {"code": -32602, "message": "x"}}))                # protocol_error
    print(classify(200, {"result": {"resultType": "partial"}}))                      # invalid_response
    print(classify(500, {"result": {"resultType": "complete"}}))                     # http_error

    return 0


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

        app_support.emit("started", id=request_id, method=method, token=token)
        outcome, status, response = run_call(options.host, options.port,
                                             request_id, method, params, token)

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