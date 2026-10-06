# MCP assignment support

This bundle supplies editable command-line starters, JSON message helpers, libraries, data, computation helpers, and development tools. It does not contain a student networking solution or a downloadable reference server. Follow the assignment specification for assessed behaviour.

## Start here

1. Run the example for your language below.
2. Follow `c/starter/README.md`, `java/starter/README.md`, or `python/starter/README.md` to copy the starting files into a new work directory. Read only your language's section in `SUPPORT.md` initially. Leave analysis and cancellation until the later phases.
3. Implement one `get_reading` request in your server and call it with the reference client below.
4. Implement the same call in your client, then complete the remaining Phase 1 requirements. Test against the hosted reference service when its address is announced on WebCMS3.

Run these commands from the bundle directory. No installation is needed on CSE. The starters report unfinished networking until you implement it.

### Python

```sh
python3 -B python/demo.py data/readings.json quick '{"station_id":"AU01"}'
python3 -B python/demo.py data/readings.json analysis '{"station_id":"AU02"}' 10
```

### C

```sh
mkdir -p build
gcc -std=c17 -Wall -Wextra -Wpedantic -DCJSON_NESTING_LIMIT=64 \
  c/demo.c c/student_tools.c c/vendor/cJSON.c -lm -o build/c-demo
build/c-demo data/readings.json quick '{"station_id":"AU01"}'
build/c-demo data/readings.json analysis '{"station_id":"AU02"}' 10
```

### Java

```sh
mkdir -p build/java
javac --release 21 -cp 'java/lib/*' -d build/java java/StudentTools.java java/Demo.java
java -cp 'build/java:java/lib/gson-2.14.0.jar' Demo data/readings.json quick '{"station_id":"AU01"}'
java -cp 'build/java:java/lib/gson-2.14.0.jar' Demo data/readings.json analysis '{"station_id":"AU02"}' 10
```

These examples call computation functions directly. They do not open sockets. In the analysis demos, `10` is a delay in milliseconds per step; the server launch option in the assignment uses seconds. A final optional integer cancels after that many steps. See the language notes for details.

## Data and expected results

`data/readings.json` contains fictional readings in chronological order. Each station has eight samples. AU01's latest temperature is 27 C and its mean is 23.5 C; AU02's latest temperature is 17 C and its mean is 13.5 C.

`schemas/tools.json` defines the three tools and their argument schemas. `schemas/data.schema.json` describes the sample data. The helpers validate the arguments; you do not implement a general schema engine.

`expected/` contains tool data for quick calls, history with limit 3, and analysis of both stations. Compare parsed values, not JSON whitespace or object-member order. These are computation results, without an MCP envelope.

`examples/` contains complete JSON-RPC request documents for discovery, listing, each tool, and unknown-tool and invalid-argument cases. Request ids and progress tokens in those files are examples. Your client allocates its own ids.

## Reference client

Start your server on loopback, then run:

```sh
reference/run.sh --host 127.0.0.1 --port 51000 --timeout 30
```

Enter JSON-lines commands:

```json
{"op":"call","name":"get_reading","arguments":{"station_id":"AU01"}}
{"op":"wait"}
```

The result should contain AU01's latest reading, 27 C. Add `discover` and `list` commands as you complete Phase 1. For streaming and cancellation, see `reference/README.md`. The reference client is a development tool, not a submission template. Its Java HTTP implementation is not permitted in your assessed networking code.

## Inspect a fragmented request

With your server running:

```sh
python3 -B tools/wire_probe.py --port 51000 \
  --request examples/analysis.json --fragment-size 7 --pause-ms 2
```

The probe prints HTTP status and headers to standard error, then displays the response body as it arrives. It is not an automatic marker. Smaller writes do not guarantee identical receive boundaries. See `tools/README.md` for usage and limits.

## Keep the bundle together

- `c/`: editable starters, computation helper, demo, cJSON 1.7.19, and licence.
- `java/`: editable starters, computation helper, demo, Gson 2.14.0, compile-time annotations, and licences.
- `python/`: editable starters, computation helper, and demo, using the standard library.
- `reference/`: runnable reference-client JAR and launcher; no source solution.
- `tools/`: manual wire-inspection tool.
- `data/`, `schemas/`, `examples/`, `expected/`: shared inputs and results.

Do not submit this entire development bundle. Include only the supplied files and libraries your programs need, retaining their licences, under the submission's `support/` directory. Keep the reference client, demos, and development output out of the submission. The assignment page defines the archive and build requirements.
