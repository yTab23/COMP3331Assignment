
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
    #Phase A: Retrieve header chunk by chunk
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



    def read_head(self):

        # waits for the header block,
        while HEADER_END not in self.buffer:
            data = self.sock.recv(1024)
            if data == b"":
                if len(self.buffer) == 0:
                    return None
                raise ConnectionError("closed mid-headers")
            self.buffer.extend(data)
        # parses it into self.start_line and the headers dict,
        header_end = self.buffer.index(HEADER_END) + 4
        header_text = self.buffer[:header_end].decode("utf-8")

        headers = {}

        lines = header_text.split("\r\n")
        self.start_line = lines[0]

        for line in header_text.split("\r\n")[1:]:     # [0] is the request/status line
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()

        # and deletes the header bytes from the buffer.

        del self.buffer[:header_end]
        # It returns the headers and stops there.
        return headers

    def _more(self):
        #Receive more bytes into the buffer.
        #EOF here is always an error
        data = self.sock.recv(1024)
        if data == b"":
            raise ConnectionError("closed mid-body")
        self.buffer.extend(data)

    def read_chunk(self):
        # Return one chunk's data as bytes, or None for the zero chunk (body finished).

        while b"\r\n" not in self.buffer:
            self._more()
        line_end = self.buffer.index(b"\r\n")
        size = int(self.buffer[:line_end].strip(), 16)

        data_start = line_end + 2
        chunk_end = data_start + size + 2
        while len(self.buffer) < chunk_end:
            self._more()

        if self.buffer[chunk_end - 2:chunk_end] != b"\r\n":
            raise ValueError("chunk is not terminated by CRLF")

        data = bytes(self.buffer[data_start:data_start + size])
        del self.buffer[:chunk_end]
        return None if size == 0 else data


"""
Work in bytes until the last moment. The buffer is a bytearray, b"\n\n" is the boundary you search for, and you only decode after you hold one complete event. Decoding each chunk separately can split a multi-byte UTF-8 character down the middle.

Use the same slicing pattern as the other buffers. Find the boundary with index, take everything before it as one event, and del that event and its two LF bytes from the front. Then loop, because one feed() call can contain several events. A single if would only catch the first.

Strip the prefix exactly. An event should start with data: , six bytes with the space. If it doesn’t, decide what to do (raise ValueError is the simplest) instead of passing it on.
Parse with parse_json, which you already import from student_tools. It decodes text, so give it event_bytes.decode("utf-8").

The leftover is state. Whatever follows the last \n\n stays in self.buffer. That’s where a half-received event waits for the next chunk.
Return a list, even when it’s empty or has one item. The caller loops over it.

"""


class SSEBuffer:
    def __init__(self):
        self.buffer = bytearray()


    def feed(self, data):
        self.buffer.extend(data)
        events = []
        while b"\n\n" in self.buffer:
            boundary = self.buffer.index(b"\n\n")
            raw = bytes(self.buffer[:boundary])
            del self.buffer[:boundary + 2]
            if not raw.startswith(b"data: "):
                raise ValueError("SSE event does not start with 'data: '")
            events.append(json.loads(raw[6:].decode("utf-8")))
        return events












