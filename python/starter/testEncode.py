import app_support
from mcp_io import encode_chunk, sse_event

event = sse_event(app_support.progress("p1", 1, 8))
print(repr(event))
print(repr(encode_chunk(event)))