# Reference client

Use this binary to exercise your MCP server. It is not a student solution or a submission template. It uses Java 21's standard HTTP client, which is permitted for this reference tool, not for the assessed student network implementation. Source is not distributed here.

Run with Java 21 and the supplied `../java/lib/gson-2.14.0.jar`. Keep the resource directories together. No compilation or installation is needed.

```sh
./run.sh --host 127.0.0.1 --port 51000 --timeout 30
```

The defaults are the values above. The endpoint is `/mcp` over HTTP/1.1. `--timeout` accepts seconds greater than zero and at most 3600. `--help` prints usage. You can also run `java -jar reference-client.jar` with the same options and directory layout.

Enter one JSON object per line:

```json
{"op":"discover"}
{"op":"wait"}
{"op":"list"}
{"op":"wait"}
{"op":"call","name":"get_reading","arguments":{"station_id":"AU01"}}
{"op":"wait"}
```

`discover` sends `server/discover`; `list` sends `tools/list`. Read the returned tool definitions and use arguments supported by your server. Tool calls require a name and an arguments object. Tool names are restricted to printable ASCII without spaces.

For overlap and cancellation, start a fresh client:

```json
{"op":"call","name":"analyse_readings","arguments":{"station_id":"AU01"}}
{"op":"call","name":"get_reading","arguments":{"station_id":"AU02"}}
```

After progress appears, cancel the slow call using its printed integer id:

```json
{"op":"cancel","id":1}
{"op":"call","name":"get_reading","arguments":{"station_id":"AU01"}}
{"op":"wait"}
```

Ids start at 1 in each process and increase for every accepted discovery, list, or tool request. Tool calls use string progress tokens `p1`, `p2`, and so on. Use the actual printed id if you have already issued requests.

Up to eight requests can run concurrently. A ninth is rejected, not queued. Each call owns its response stream. Cancelling one call closes that stream or interrupts its pending HTTP exchange without shutting down other calls. Cancellation is not proof that the server stopped computation or that an operation had no effect.

`wait` blocks command input until all current calls finish, then emits `idle`. Do not put it before a cancellation command that needs to run during a call. EOF drains active calls under their original deadlines, emits `idle`, and exits. Ctrl-C terminates the process rather than providing per-call completion events.

Stdout contains flushed JSON-lines events:

- `started`: `id`, MCP `method`, and `token` (null for discovery/list).
- `progress`: `id`, `token`, and the received progress `params` object.
- `finished`: `id`, `outcome`, and `http_status` when known. A validated final JSON-RPC envelope is included as `response` when received.
- `cancel_requested`: the `id` whose cancellation was accepted.
- `idle`: no active requests remain.
- `input_error`: a `message` explaining a rejected command.

Finished outcomes are `success`, `tool_error`, `protocol_error`, `http_error`, `invalid_response`, `network_error`, `timeout`, `cancelled`, or `client_bug`. A JSON-RPC error takes precedence over its HTTP error status. Inspect `outcome`, not just the presence of `response`: a final envelope can arrive before a body subsequently stalls or fails. Success is emitted only after consuming the complete HTTP body. Diagnostics go to stderr.

Malformed commands leave input usable. An oversized input line stops further input, drains calls, and exits 2. Invalid launch options also exit 2. Normal EOF exits 0 even if individual calls failed; inspect their events.

The deadline starts when a validated request is accepted. It includes sending, receiving progress, receiving the final response, and consuming the rest of the body. Progress does not extend it. Keep stdout/stderr consumed and the process scheduled; blocked output is not covered by a separate watchdog.

This is a bounded teaching client for MCP revision `2026-07-28`, not a general MCP implementation. It accepts JSON and SSE responses, checks numeric request ids and string progress tokens without coercion, and parses JSON with Gson `Strictness.STRICT`. Stdin lines, serialized requests, and decoded HTTP response bodies are limited to 4 MiB each; JSON nesting is limited to 128. Request ids and error codes use signed 32-bit integers. Malformed UTF-8, unsupported content types or compression, unknown notifications, and non-complete results are rejected. Failed or cancelled bodies may be closed before being fully consumed.

There is no initialization handshake, version fallback, pagination, schema interpreter, subscription, stream replay, TLS, authentication, or application-level retry. SSE comments and unknown SSE fields are ignored; JSON message fields determine routing. SSE events without a terminating blank line are discarded. HTTP framing and persistent connection reuse are delegated to Java, so this binary is not an oracle for every detail of the assessed raw-socket HTTP profile.

The client sets OpenJDK's `jdk.httpclient.disableRetryConnect=true` and `jdk.httpclient.enableAllMethodRetry=false`, and disables redirects. Java's public HTTP API does not guarantee that every internal retry is disabled. Treat interrupted or failed operations as potentially having reached the server; do not use this tool for operations where an uncertain repeat would be unsafe.

Gson is supplied separately in `../java/lib/`; retain the licence files shipped there. This jar does not embed Gson.
