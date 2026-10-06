# Python starting files

From the bundle root, copy into a new, empty work directory:

```sh
mkdir work-python
cp python/starter/client.py python/starter/server.py python/starter/app_support.py work-python/
mkdir -p work-python/support/python work-python/support/data
cp python/student_tools.py work-python/support/python/
cp data/readings.json work-python/support/data/
cp -R schemas work-python/support/
cd work-python
python3 -B client.py --help
python3 -B server.py --help
```

The entry files parse options and the client reads JSON-lines commands. They deliberately report that networking is not implemented and exit 2 when asked to perform work. They do not open sockets or demonstrate a completed phase. Edit them directly; no framework or required class hierarchy is imposed.

`app_support.py` supplies these editable functions:

- `client_options()` and `server_options()`: the published options; timeout and analysis delay are seconds.
- `emit(event, **fields)`: one flushed JSON output record, serialized across threads.
- `request(id, method, parameters, token=None)`: a JSON-RPC request with fixed MCP metadata. Omit the token for Phase 1; supply `p1`, for example, when requesting progress later.
- `result(id, fields)`: a completed result envelope.
- `error(id, code, message)`: a protocol error for a readable request id.
- `progress(token, done, total)`: a progress notification, not an HTTP or SSE message.

The constructors return ordinary dictionaries. For example:

```python
from app_support import request
import json

message = request(1, "tools/call", {
    "name": "get_reading", "arguments": {"station_id": "AU01"},
})
body = json.dumps(message, ensure_ascii=False, allow_nan=False).encode("utf-8")
# The HTTP Content-Length is len(body), not the number of characters.
```

For a tool response, pass `{"content": [{"type": "text", "text": json.dumps(data)}]}` as the result fields. A known tool failure uses a text message and `"isError": True`. Discovery and listing use the fields shown in the assignment's worked examples and supplied schemas.

Load data once using `load_dataset("support/data/readings.json")` from `support.python.student_tools`. See `SUPPORT.md` in the bundle for the computation interface. You implement socket I/O, HTTP framing, dispatch, SSE processing, connection reuse, active-call state, deadlines, and cleanup. The helpers do not allocate ids, start workers, manage sockets, or cancel calls for you.
