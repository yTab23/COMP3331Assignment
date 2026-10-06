"""Manual HTTP observer, not a response validator or grading tool."""

import argparse
import http.client
import json
import math
from pathlib import Path
import re
import signal
import socket
import sys
import time


EXCHANGE_SECONDS = 30
META = "io.modelcontextprotocol/"


def reject_constant(value):
    raise ValueError("Nonfinite JSON number: " + value)


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON number is outside the finite float range")
    return number


def header_value(value, field):
    if not isinstance(value, str) or not value or any(
        not 33 <= ord(character) <= 126 for character in value
    ):
        raise ValueError(field + " must be nonempty ASCII without whitespace or controls")
    return value


def request_bytes(path, host, port):
    with Path(path).open("rb") as source:
        body = source.read(1024 * 1024 + 1)
    if len(body) > 1024 * 1024:
        raise ValueError("Request file exceeds 1 MiB")
    request = json.loads(
        body.decode("utf-8"), parse_constant=reject_constant, parse_float=finite_float,
    )
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        raise ValueError("Request file must contain one JSON-RPC 2.0 object")
    if type(request.get("id")) not in (int, str):
        raise ValueError("Request id must be an integer or string, not a boolean")
    method = header_value(request.get("method"), "method")
    params = request.get("params")
    if not isinstance(params, dict) or not isinstance(params.get("_meta"), dict):
        raise ValueError("Request needs params._meta")
    meta = params["_meta"]
    version = header_value(meta.get(META + "protocolVersion"), "protocolVersion")
    if not isinstance(meta.get(META + "clientCapabilities"), dict):
        raise ValueError("Request metadata needs a clientCapabilities object")
    authority = f"[{host}]" if ":" in host else host
    headers = [
        "POST /mcp HTTP/1.1",
        f"Host: {authority}:{port}",
        "Content-Type: application/json",
        "Accept: application/json, text/event-stream",
        "MCP-Protocol-Version: " + version,
        "Mcp-Method: " + method,
        f"Content-Length: {len(body)}",
        "Connection: close",
    ]
    if method == "tools/call":
        headers.append("Mcp-Name: " + header_value(params.get("name"), "name"))
    return ("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + body


def deadline_expired(signum, frame):
    raise TimeoutError(f"Whole exchange exceeded {EXCHANGE_SECONDS} seconds")


def observe(host, port, wire, fragment_size, pause_ms):
    previous_handler = signal.signal(signal.SIGALRM, deadline_expired)
    signal.setitimer(signal.ITIMER_REAL, EXCHANGE_SECONDS)
    try:
        with socket.create_connection((host, port)) as sock:
            size = fragment_size or len(wire)
            for offset in range(0, len(wire), size):
                if offset:
                    time.sleep(pause_ms / 1000)
                sock.sendall(wire[offset:offset + size])
            with http.client.HTTPResponse(sock) as response:
                response.begin()
                version = {10: "1.0", 11: "1.1"}.get(response.version, str(response.version))
                print(f"HTTP/{version} {response.status} {response.reason}", file=sys.stderr)
                for name, value in response.getheaders():
                    print(f"{name}: {value}", file=sys.stderr)
                print(file=sys.stderr, flush=True)
                while data := response.read1(4096):
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="hostname or unbracketed IP address")
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--request", required=True, help="path to a complete JSON-RPC request")
    parser.add_argument("--fragment-size", type=int, help="bytes per sendall, including headers")
    parser.add_argument("--pause-ms", type=float, default=0, help="pause between writes")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", args.host):
        parser.error("host must be an ASCII hostname or unbracketed IP address")
    if not 1 <= args.port <= 65535:
        parser.error("port must be from 1 to 65535")
    if args.fragment_size is not None and args.fragment_size < 1:
        parser.error("fragment-size must be positive")
    if not math.isfinite(args.pause_ms) or args.pause_ms < 0:
        parser.error("pause-ms must be finite and nonnegative")
    if args.pause_ms and args.fragment_size is None:
        parser.error("pause-ms requires fragment-size")
    if not hasattr(signal, "setitimer"):
        parser.error("this probe requires Unix interval timers")
    try:
        wire = request_bytes(args.request, args.host, args.port)
        observe(args.host, args.port, wire, args.fragment_size, args.pause_ms)
    except KeyboardInterrupt:
        print("Interrupted; connection closed", file=sys.stderr)
        return 130
    except (OSError, ValueError, http.client.HTTPException) as error:
        print("Probe: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
