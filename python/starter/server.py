"""Server entry point. Implement accepting and serving TCP connections here."""

import sys

from app_support import server_options


"""
handle_request(headers, body) in server.py. It returns (status, payload_dict) and never touches a socket, so you can test it by calling it directly. It dispatches on body["method"]:

server/discover returns app_support.result(id, {"supportedVersions": [...], "capabilities": {...}}).

tools/list returns result(id, {"tools": TOOLS}).

tools/call looks up params["name"] in a dict of get_reading/get_history/analyse_readings. For now, treat analyse_readings as a plain call that returns JSON. Streaming is Phase 2.

An unknown method returns (404, error(id, -32601, ...)).

An unknown tool returns (400, error(id, -32602, ...)), without running anything.

If the tool raises ValueError, return HTTP 200 with a completed result carrying isError: true. That’s a tool failure, not a JSON-RPC error.

Reuse the request id exactly as received, whatever its type.

"""
def handle_request(headers, body):
    print()


def main():
    options = server_options()
    print(f"Starter only: server on port {options.port} is not implemented",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
