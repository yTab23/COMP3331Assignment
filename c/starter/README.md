# C starter

Editable source, not a networking solution. `client.c` and `server.c` are the entry points; `starter.c`/`starter.h` supply launch parsing, flushed thread-safe JSON-lines output, and four JSON-RPC constructors. No sockets, HTTP, SSE, dispatch, request tracking, workers, deadlines, or cancellation are implemented. The supplied computations remain under `support/c/`.

From the unpacked bundle root (the directory containing `c/`, `java/`, and `data/`), copy into a new empty work directory:

```sh
work=$(mktemp -d /tmp/mcp-c-work.XXXXXX)
mkdir -p "$work/support/c"
cp c/starter/client.c c/starter/server.c c/starter/starter.c c/starter/starter.h c/starter/Makefile "$work/"
cp c/student_tools.c c/student_tools.h "$work/support/c/"
cp -R c/vendor "$work/support/c/"
cp -R data schemas "$work/support/"
cd "$work"
make
./client --help
./server --help
./server --port 51000 --analysis-delay 0.5
printf '%s\n' '{"op":"call","name":"get_reading","arguments":{"station_id":"AU01"}}' \
  | ./client --host 127.0.0.1 --port 51000 --timeout 30
```

These are separate shell commands, not a success-only `&&` chain. The server prints `starter-not-implemented` to stderr and exits 1 without listening. The client parses each command, prints `{"event":"input_error","message":"starter-not-implemented"}`, then reports unfinished EOF cleanup on stderr and exits 1. This is intentional: `discover`, `list`, `call`, `cancel`, and `wait` do not perform work yet. No `started`, `finished`, or `idle` event is fabricated. Help exits 0. Bad launch options exit 2.

`make` builds both programs with system GCC and the copied cJSON sources; no installation is needed. Keep the vendored licences. After implementing networking, run the same server and client commands in separate terminals on the same machine. The server binds to loopback; the endpoint is `/mcp`. Defaults are host `127.0.0.1`, port `51000`, timeout `30` seconds, and analysis delay `0.5` seconds. Options use separate values, such as `--timeout 10`.

## JSON helpers

Include `starter.h`. Local commands are parsed with `student_parse_json`; `client.c` owns and deletes each parsed tree, including its children. Before starting a worker, either clone the needed JSON or explicitly transfer the tree and its deletion responsibility to that worker. Do not retain child pointers after the loop deletes the command. `starter_output(value)` borrows a tree, prints one compact line and flushes under a stdout lock; check its boolean return. Use it for all client event output, not for sending network bytes. Do not mutate a tree while another thread serializes it.

The constructors copy their JSON inputs; callers retain ownership of inputs and own each returned tree. Delete returned trees with `cJSON_Delete`. Allocation failure is fatal with a diagnostic, not a partial envelope. The helpers assume valid input shapes; they are constructors, not validators.

```c
/* id is your allocated request id; params contains name/arguments for a call,
 * or is an empty object for discovery/list. token is optional (NULL to omit). */
cJSON *request = starter_request(id, "tools/call", params, token);

/* fields is the result object before resultType is added. */
cJSON *response = starter_completed(id, fields);
cJSON *error = starter_error(id, -32601, "Method not found", NULL);
cJSON *progress = starter_progress(token, 1, 8);

/* Serialize each when needed for your own HTTP/SSE writer. */
char *text = cJSON_PrintUnformatted(request);
if (text == NULL) {
    /* Report failure and stop this operation. */
} else {
    /* Your transport sends strlen(text) UTF-8 bytes with the required framing. */
    cJSON_free(text);
}
cJSON_Delete(request);
cJSON_Delete(response);
cJSON_Delete(error);
cJSON_Delete(progress);
```

`starter_request` replaces `params._meta` with protocol version `2026-07-28`, empty client capabilities, and the optional progress token. It does not allocate ids/tokens or create HTTP headers. `starter_completed` replaces `fields.resultType` with `"complete"`; other fields are copied unchanged. IDs and tokens retain their JSON types.

For discovery, `fields` contains `supportedVersions` and `capabilities`; for listing it contains `tools`. For a tool result, build `fields` with `content: [{"type":"text","text":...}]` and `isError`. Serialize the successful `StudentResult.json` into the text field, or use the tool's error message with `isError: true`. Do not pass raw weather data as the entire MCP result. Check `StudentResult.status` first; cancellation sends no result on the closed connection. Free `StudentResult.json`, and free serialized text with `cJSON_free` after copying it into a JSON string.

`starter_error` omits id or error data when the corresponding argument is NULL. For assessed unknown-method/tool errors, pass the request id and code `-32601`/`-32602` respectively. `starter_progress` has no id; a negative total omits `params.total`. It only constructs JSON, not an SSE event.

## Student-owned work

Replace the visible failure paths in the entry files. Implement framing, method/tool dispatch, socket I/O, response matching, reuse, overlapping calls, cancellation, deadlines, and cleanup. Grading guarantees valid local commands, request envelopes, version, metadata, and mirrored headers; no general validator is needed. SSE uses one compact `data: {JSON}\n\n` event with LF endings, but events can still span chunks/reads or arrive together. Load `support/data/readings.json` and `support/schemas/tools.json` in your server; validate the dataset once and keep it read-only. Connect `analyse_readings` progress/wait hooks to that call's transport and stop state. Keep mutable request state separate. Do not replace the stub with a local computation pretending to be a server.

See the bundle's `SUPPORT.md`, `c/demo.c`, and `reference/README.md` for computation ownership, hook usage, and the required client event fields. The demo is not copied into this work directory. Keep the entry files at the submission root and dependencies under `support/`.
