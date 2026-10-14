import socket, threading, time
import app_support
from mcp_io import Connection, encode_chunk, sse_event, LAST_CHUNK
from client import read_response

HEAD = (b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n"
        b"Transfer-Encoding: chunked\r\n\r\n")
final_msg = app_support.result(1, {"content": [{"type": "text", "text": "x"}], "isError": False})
events = [sse_event(app_support.progress("p1", 1, 3)),
          sse_event(app_support.progress("p1", 2, 3)),
          sse_event(final_msg)]
joined = b"".join(events)
cut = len(events[0]) - 1          # between the two LF bytes that end the first event

bodies = {
    "one event per chunk":      b"".join(encode_chunk(e) for e in events) + LAST_CHUNK,
    "all events in one chunk":  encode_chunk(joined) + LAST_CHUNK,
    "event split across chunks": encode_chunk(joined[:50]) + encode_chunk(joined[50:]) + LAST_CHUNK,
    "event end split in half":  encode_chunk(joined[:cut]) + encode_chunk(joined[cut:]) + LAST_CHUNK,
}


def run(label, payload, step):
    a, b = socket.socketpair()
    b.settimeout(5)                               # a hang becomes an error, not a frozen test
    def sender():
        for i in range(0, len(payload), step):
            a.sendall(payload[i:i + step])
            time.sleep(0.001)
    threading.Thread(target=sender, daemon=True).start()
    seen = []
    status, final, _ = read_response(Connection(b), 1, "p1", lambda p: seen.append(p["progress"]))
    print(f"{label:28} step {step:4} -> {status} {seen} id={final['id']}")


for label, body in bodies.items():
    payload = HEAD + body
    for step in (len(payload), 7, 1):             # all at once, 7 bytes, 1 byte
        run(label, payload, step)

def cut_off(label, payload):
    a, b = socket.socketpair()
    b.settimeout(5)
    a.sendall(payload)
    a.close()                                    # EOF after the partial data
    try:
        read_response(Connection(b), 1, "p1")
        print(label, "-> NO ERROR (bug)")
    except Exception as exc:
        print(label, "->", type(exc).__name__ + ":", exc)

full = HEAD + bodies["one event per chunk"]
cut_off("closed before the zero chunk", full[:-len(LAST_CHUNK)])
cut_off("closed after only progress",   HEAD + encode_chunk(events[0]) + LAST_CHUNK)
cut_off("closed mid-chunk",             HEAD + encode_chunk(events[0])[:20])