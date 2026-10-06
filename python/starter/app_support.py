"""Editable command-line and JSON helpers. No networking or call lifecycle."""

import argparse
import json
import math
import threading

VERSION = "2026-07-28"
_output_lock = threading.Lock()


def _port(value):
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("port must be an integer from 1 to 65535") from error
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be an integer from 1 to 65535")
    return port


def _seconds(value):
    try:
        seconds = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("time must be a finite nonnegative number") from error
    if not math.isfinite(seconds) or seconds < 0:
        raise argparse.ArgumentTypeError("time must be a finite nonnegative number")
    return seconds


def _timeout(value):
    seconds = _seconds(value)
    if seconds == 0:
        raise argparse.ArgumentTypeError("timeout must be positive")
    return seconds


def client_options():
    parser = argparse.ArgumentParser(description="MCP client starter")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=_port, default=51000)
    parser.add_argument("--timeout", type=_timeout, default=30)
    return parser.parse_args()


def server_options():
    parser = argparse.ArgumentParser(description="MCP server starter")
    parser.add_argument("--port", type=_port, default=51000)
    parser.add_argument("--analysis-delay", type=_seconds, default=0.5)
    return parser.parse_args()


def emit(event, **fields):
    line = json.dumps({"event": event, **fields}, ensure_ascii=False, allow_nan=False)
    with _output_lock:
        print(line, flush=True)


def request(request_id, method, parameters, token=None):
    meta = {
        "io.modelcontextprotocol/protocolVersion": VERSION,
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    if token is not None:
        meta["progressToken"] = token
    return {"jsonrpc": "2.0", "id": request_id, "method": method,
            "params": {**parameters, "_meta": meta}}


def result(request_id, fields):
    return {"jsonrpc": "2.0", "id": request_id,
            "result": {**fields, "resultType": "complete"}}


def error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id,
            "error": {"code": code, "message": message}}


def progress(token, done, total=None):
    params = {"progressToken": token, "progress": done}
    if total is not None:
        params["total"] = total
    return {"jsonrpc": "2.0", "method": "notifications/progress", "params": params}
