# Java starter

Editable source, not a networking solution. `Client.java` and `Server.java` are default-package entry classes; `Starter.java` supplies launch parsing, flushed thread-safe JSON-lines output, and four JSON-RPC constructors. No sockets, HTTP, SSE, dispatch, request tracking, workers, deadlines, or cancellation are implemented. The supplied computations remain under `support/java/`.

From the unpacked bundle root (the directory containing `c/`, `java/`, and `data/`), copy into a new empty work directory:

```sh
work=$(mktemp -d /tmp/mcp-java-work.XXXXXX)
mkdir -p "$work/support/java"
cp java/starter/Client.java java/starter/Server.java java/starter/Starter.java java/starter/Makefile "$work/"
cp java/StudentTools.java "$work/support/java/"
cp -R java/lib "$work/support/java/"
cp -R data schemas "$work/support/"
cd "$work"
make
java -cp '.:support/java:support/java/lib/*' Client --help
java -cp '.:support/java:support/java/lib/*' Server --help
java -cp '.:support/java:support/java/lib/*' Server --port 51000 --analysis-delay 0.5
printf '%s\n' '{"op":"call","name":"get_reading","arguments":{"station_id":"AU01"}}' \
  | java -cp '.:support/java:support/java/lib/*' Client --host 127.0.0.1 --port 51000 --timeout 30
```

These are separate shell commands, not a success-only `&&` chain. The server prints `starter-not-implemented` to stderr and exits 1 without listening. The client parses each command, prints `{"event":"input_error","message":"starter-not-implemented"}`, then reports unfinished EOF cleanup on stderr and exits 1. This is intentional: `discover`, `list`, `call`, `cancel`, and `wait` do not perform work yet. No `started`, `finished`, or `idle` event is fabricated. Help exits 0. Bad launch options exit 2.

`make` builds both programs with Java 21 and the copied Gson/annotation JARs; no installation is needed. Keep their licences. After implementing networking, run the same server and client commands in separate terminals on the same machine. The server binds to loopback; the endpoint is `/mcp`. Defaults are host `127.0.0.1`, port `51000`, timeout `30` seconds, and analysis delay `0.5` seconds. Options use separate values, such as `--timeout 10`. Convert analysis delay to milliseconds when calling `StudentTools.analyseReadings`.

## JSON helpers

`Client` reads UTF-8 lines and uses `StudentTools.parseJson` for strict parsing. `Starter.output(value)` synchronizes serialization, one-line output and flush; output failure throws `IOException`. Use it for all client events, not for sending network bytes. Do not mutate a tree while another thread serializes it.

Constructors copy their JSON inputs and assume valid input shapes; they are not validators. With Gson's `JsonObject` and `JsonElement` imports:

```java
// id is your allocated request id; params contains name/arguments for a call,
// or is an empty object for discovery/list. token is optional (null to omit).
JsonObject request = Starter.request(id, "tools/call", params, token);

// fields is the result object before resultType is added.
JsonObject response = Starter.completed(id, fields);
JsonObject error = Starter.error(id, -32601, "Method not found", null);
JsonObject progress = Starter.progress(token, 1, 8);

// Your transport sends these bytes with its own HTTP/SSE framing.
byte[] body = request.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);
```

`Starter.request` replaces `params._meta` with protocol version `2026-07-28`, empty client capabilities, and the optional progress token. It does not allocate ids/tokens or create HTTP headers. `Starter.completed` replaces `fields.resultType` with `"complete"`; other fields are copied unchanged. IDs and tokens retain their JSON types.

For discovery, `fields` contains `supportedVersions` and `capabilities`; for listing it contains `tools`. For a tool result, build `fields` with `content: [{"type":"text","text":...}]` and `isError`. Serialize the successful computation's JSON into the text field, or use the tool's error message with `isError: true`. Do not pass raw weather data as the entire MCP result. Handle `StudentTools.InvalidArguments` as a tool error; `StudentTools.Cancelled` sends no result on the closed connection.

`Starter.error` omits id or error data when the corresponding argument is null. For assessed unknown-method/tool errors, pass the request id and code `-32601`/`-32602` respectively. `Starter.progress` has no id; a negative total omits `params.total`. It only constructs JSON, not an SSE event.

## Student-owned work

Replace the visible failure paths in the entry files. Implement framing, method/tool dispatch, socket I/O, response matching, reuse, overlapping calls, cancellation, deadlines, and cleanup. Grading guarantees valid local commands, request envelopes, version, metadata, and mirrored headers; no general validator is needed. SSE uses one compact `data: {JSON}\n\n` event with LF endings, but events can still span chunks/reads or arrive together. Load `support/data/readings.json` and `support/schemas/tools.json` in your server; construct `StudentTools` once from the dataset. Connect its analysis progress/wait hooks to that call's transport and stop state. Keep mutable request state separate. Do not replace the stub with a local computation pretending to be a server.

See the bundle's `SUPPORT.md`, `java/Demo.java`, and `reference/README.md` for computation interfaces, hook usage, and the required client event fields. The demo is not copied into this work directory. Keep the entry files at the submission root and dependencies under `support/`.
