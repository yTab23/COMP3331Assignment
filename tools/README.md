# Wire observer

`wire_probe.py` is a manual observation aid, not an automated test suite, response validator, reference client, or grading tool. It uses Python's standard library and requires Unix interval timers, as available on Linux. No installation is needed.

Start your server separately. From the bundle root (`student-resources`), substitute its listening port:

```sh
python3 -B tools/wire_probe.py --port 51000 --request examples/reading.json
python3 -B tools/wire_probe.py --port 51000 --request examples/analysis.json
python3 -B tools/wire_probe.py --port 51000 --request examples/analysis.json --fragment-size 7 --pause-ms 2
python3 -B tools/wire_probe.py --host 127.0.0.1 --port 51000 --request /absolute/path/to/request.json
```

`--host` defaults to `127.0.0.1`. `--request` accepts any file path, not just bundled examples. Supply one complete UTF-8 JSON-RPC request with an integer or string id, method, and `params._meta` containing `io.modelcontextprotocol/protocolVersion` and `io.modelcontextprotocol/clientCapabilities`. The bundled examples include these fields. A `tools/call` also supplies `params.name` and its tool arguments. The probe does not fill in or rewrite the JSON body. Files are limited to 1 MiB. Trailing text, nonfinite numbers, boolean ids, and unsafe header-source characters are rejected before connecting.

The probe constructs `POST /mcp` with matching version, method, and tool-name headers, both accepted response content types, and the byte `Content-Length` of the original file, including its whitespace. Hostnames and header values cannot contain CR, LF, or other controls. It sends through a raw socket and uses `http.client.HTTPResponse` only to read the response.

Status and headers go to stderr. The HTTP-decoded body goes incrementally to stdout with a flush after every read: chunk framing is removed, but JSON and SSE bytes are otherwise unchanged. There is no JSON/SSE parsing, pretty-printing, character transcoding, content decompression, or final-result check. You can pipe or redirect stdout to inspect the body independently. HTTP error statuses are displayed, not graded. Exit 0 means the reader returned normally, not that the server or response is correct. Input/I/O errors exit 1; CLI usage errors exit 2.

One 30-second deadline covers connection setup, all writes, fragmentation pauses, and response reading. Progress does not reset it. Ctrl-C closes the connection and exits 130. Each invocation uses one connection with `Connection: close`; it does not demonstrate connection reuse or prove that server computation stopped after disconnecting.

`--fragment-size N` limits each `sendall` buffer, including request headers. `--pause-ms` adds a finite nonnegative delay between those writes and requires fragmentation. TCP can split or combine writes: receiving read boundaries are not guaranteed by write sizes. Likewise, stdout reads need not align with HTTP chunks or SSE events.

This tool owns only the manual exchange. Students still implement their own protocol and networking code; the use of an HTTP reader here does not change the assignment's implementation allowance. No server, assertions, scoring, or persistent logs are included.
