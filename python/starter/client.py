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


import threading
import traceback

lock = threading.Lock()          # protects idle and active
active = {}                      # request_id -> Call


class Call:
    def __init__(self, call_id, method, token):
        self.id = call_id
        self.method = method
        self.token = token
        self.thread = None
        self.conn = None          # the connection this call is using right now
        self.cancelled = False

idle = []

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

def run_call(host, port, request_id, method, parameters, token=None, on_progress=None, on_connect=None):
    try:
        status, response = exchange(host, port, request_id, method, parameters,
                                    token, on_progress, on_connect)
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


def take_connection(host, port):
    with lock:
        if idle:
            return idle.pop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except BaseException:
        sock.close()
        raise
    return Connection(sock)


def give_back(conn, headers):
    if headers.get("connection", "").lower() == "close" or conn.buffer:
        conn.sock.close()
    else:
        with lock:
            idle.append(conn)

def exchange(host, port, request_id, method, parameters, token=None, on_progress=None,on_connect=None):
    request = app_support.request(request_id, method, parameters, token)
    conn = take_connection(host, port)
    try:
        if on_connect:
            on_connect(conn)                  # register the connection (raises if already cancelled)
        conn.sock.sendall(build_request(request, host, port))
        status, final, headers = read_response(conn, request_id, token, on_progress)
        if on_connect:
            on_connect(None)                  # detach before the pool can see it
    except BaseException:
        conn.sock.close()
        raise
    give_back(conn, headers)
    return status, final

def same_value(a, b):
    """Equal in value and JSON type: 17 is not "17", and 1 is not True."""
    return type(a) is type(b) and a == b

def run_worker(call, host, port, params):
    def on_progress(p):                         # closes over this call, so no late-binding bug
        app_support.emit("progress", id=call.id, token=call.token, params=p)
    def attach(conn):
        print("DEBUG attach:", conn, file=sys.stderr)    # temporary
        with lock:
            call.conn = conn
    try:
        outcome, status, response = run_call(host, port, call.id, call.method,
                                             params, call.token, on_progress, attach)
        if call.cancelled and outcome in ("network_error", "invalid_response"):
            outcome, status, response = "cancelled", None, None
    except Exception:
        traceback.print_exc()                   # a bug in the client, but still report the call
        outcome, status, response = "client_bug", None, None

    fields = {"id": call.id, "outcome": outcome}
    if status is not None:
        fields["http_status"] = status
    if response is not None:
        fields["response"] = response
    app_support.emit("finished", **fields)
    with lock:
        del active[call.id]


def wait_for_calls():
    with lock:
        threads = [c.thread for c in active.values()]
    for t in threads:
        t.join()


def cancel_call(call):
    with lock:
        call.cancelled = True
        conn = call.conn
    print("DEBUG cancel: conn is", conn, file=sys.stderr)   # temporary
    if conn is not None:
        try:
            conn.sock.shutdown(socket.SHUT_RDWR)   # wakes a thread blocked in recv()
        except OSError:
            pass
        conn.sock.close()
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

        if op == "wait":                              # <-- snippet 1 replaces this branch
            wait_for_calls()
            app_support.emit("idle")
            continue
        if op == "cancel":
            cid = command.get("id")
            with lock:
                call = active.get(cid) if type(cid) is int else None
            if call is None:
                app_support.emit("input_error", message="no active call with that id")
                continue
            app_support.emit("cancel_requested", id=cid)
            cancel_call(call)
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

        request_id = next_id
        next_id += 1
        call = Call(request_id, method, token)
        call.thread = threading.Thread(target=run_worker,
                                       args=(call, options.host, options.port, params),
                                       daemon=True)
        with lock:
            active[request_id] = call
        app_support.emit("started", id=request_id, method=method, token=token)
        call.thread.start()                     # main goes straight back to reading stdin

    wait_for_calls()
    with lock:
        for conn in idle:
            conn.sock.close()
        idle.clear()
    app_support.emit("idle")
    return 0

if __name__ == "__main__":
    sys.exit(main())