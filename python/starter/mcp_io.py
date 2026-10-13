
import json

HEADER_END = b"\r\n\r\n"
REASONS = {200: "OK", 400: "Bad Request", 404: "Not Found" }
LAST_CHUNK = b"0\r\n\r\n"

def sse_event(payload):
    text = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    return b"data: " + text.encode("utf-8") + b"\n\n"



def encode_chunk(data):
    return ("%x" % len(data)).encode("ascii") + b"\r\n" + data + b"\r\n"


def build_response(status, payload):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")   # serialize first
    head = (
            f"HTTP/1.1 {status} {REASONS[status]}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "\r\n"
    )
    return head.encode("ascii") + body

def build_request(payload, host, port):
    body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
    meta = payload["params"]["_meta"]
    lines = [
        "POST /mcp HTTP/1.1",
        f"Host: {host}:{port}",
        "Content-Type: application/json",
        "Accept: application/json, text/event-stream",
        "MCP-Protocol-Version: " + meta["io.modelcontextprotocol/protocolVersion"],
        "Mcp-Method: " + payload["method"],
    ]
    if payload["method"] == "tools/call":
        lines.append("Mcp-Name: " + payload["params"]["name"])
    lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode("ascii") + body

class Connection:
    def __init__(self, sock):
        self.sock = sock
        self.buffer = bytearray()


    def read_message(self):
        while HEADER_END not in self.buffer:
            data = self.sock.recv(1024)
            if data == b"":
                if len(self.buffer) == 0:
                    return None
                raise ConnectionError("closed mid-headers")
            self.buffer.extend(data)

    # Phase B: Parse and decode only the header bytes
        header_end = self.buffer.index(HEADER_END) + 4
        header_text = self.buffer[:header_end].decode("utf-8")

        headers = {}

        lines = header_text.split("\r\n")
        self.start_line = lines[0]              # e.g. "HTTP/1.1 200 OK"

        for line in header_text.split("\r\n")[1:]:     # [0] is the request/status line
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()

        content_length = int(headers["content-length"])
        total = header_end + content_length

        # Phase C: wait until the whole message is in the buffer
        while len(self.buffer) < total:
            data = self.sock.recv(1024)
            if data == b"":
                raise ConnectionError("closed mid-body")
            self.buffer.extend(data)

        body = json.loads(self.buffer[header_end:total].decode("utf-8"))

        del self.buffer[:total]            # consume exactly one message, keep the rest
        return headers, body











