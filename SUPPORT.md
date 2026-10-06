# Using the supplied computations

The helpers read fictional weather data and return ordinary JSON values. They do not implement sockets, HTTP, SSE, MCP envelopes, or request dispatch. Your server handles those parts.

Run the examples in the bundle README before integrating a helper into your server. The demo command names are local helper demonstrations, not MCP methods.

## Arguments and results

All tools take an argument object with the fields below. Missing or extra fields and unknown station ids are argument errors.

- `get_reading`: `station_id`, a string. Returns `station_id` and `reading`.
- `get_history`: `station_id` and `limit`, an integer-valued number from 1 to 1000. Returns `station_id` and `readings`, in chronological order. A limit above the available count returns all readings.
- `analyse_readings`: `station_id`. Returns `station_id`, `count`, and `mean_temperature_c`.

For `limit`, `1`, `1.0`, and `1e0` are equivalent. Booleans, strings, and fractions such as `1.5` are invalid. The schemas are in `schemas/tools.json`; dataset-backed results are in `expected/`.

The helpers do not modify their inputs. Quick/history results contain independent copies. Keep the loaded dataset unchanged while calls use it. Analysis adds the temperatures and rounds the mean to two decimal places.

## Python

Import `python/student_tools.py` through your application's normal module path.

```python
dataset = student_tools.load_dataset("support/data/readings.json")
result = student_tools.get_reading(dataset, {"station_id": "AU01"})
```

Use `parse_json` for one complete JSON document. It rejects nonfinite numbers and trailing input. Use the standard `json` module to serialize returned data.

`get_reading` and `get_history` take the loaded dataset and parsed argument object. Invalid arguments raise `ValueError`.

`analyse_readings(dataset, arguments, step_delay, progress, stop)` takes a delay in seconds, a `progress(done, total)` callback, and a caller-owned `threading.Event`. Setting the event interrupts the wait and raises `Cancelled`. The callbacks run on the calling thread. See `python/demo.py` for a complete example.

## C

Use `c/student_tools.h`, `c/student_tools.c`, and the supplied cJSON files. Parse a complete document with `student_parse_json(text, length)`, where length excludes the terminating NUL. Validate the dataset once with `student_valid_dataset`.

Pass the parsed argument tree directly to `get_reading` or `get_history`. You do not need the original argument text or another parser. Each returns a `StudentResult`:

- `STUDENT_OK`: `json` is an owned result tree.
- `STUDENT_INVALID_ARGUMENT`: the tool rejected its input.
- `STUDENT_CANCELLED`: analysis was cancelled.
- `STUDENT_NO_MEMORY` or `STUDENT_COMPUTATION_ERROR`: computation could not complete.

Check the status before using the result. Free owned JSON trees with `cJSON_Delete`. Free text returned by `cJSON_PrintUnformatted` with `cJSON_free`. Error strings are static; do not free them. Do not change cJSON allocation hooks during use.

`analyse_readings` also takes a delay in seconds, a progress callback, a wait/stop callback, and your context pointer. The wait callback waits up to the supplied delay and returns true if cancelled. It also receives a zero-delay final check. Your context can contain the call's stop flag and progress-delivery state. Both callbacks run on the calling thread. See `c/demo.c` for usage and `c/student_tools.h` for signatures.

The supplied parser wrapper rejects trailing documents and NUL-bearing strings that cJSON cannot represent safely. cJSON has other syntax limitations; the assignment does not ask you to turn it into a general JSON conformance checker.

## Java

Use `StudentTools.parseJson` for strict parsing, then construct `new StudentTools(dataset)` once. The constructor validates and copies the dataset. `getReading` and `getHistory` accept parsed argument objects and return independent `JsonObject` values.

Invalid arguments raise `StudentTools.InvalidArguments`. Analysis cancellation raises `StudentTools.Cancelled`. These are different outcomes.

`analyseReadings(arguments, stepDelayMillis, progress, stop)` takes a delay in milliseconds, a `Progress.update(done, total)` callback, and a `WaitStop.await(delayMillis)` callback. The wait callback returns true when cancelled, including a zero-delay final check. You own the stop state and synchronization. Thread interruption is treated as cancellation and its cause is preserved. See `java/Demo.java` for a complete example.

Do not replace strict parsing with Gson's default lenient parsing. Use the supplied Gson JAR at runtime. The annotations JAR in `java/lib/` is only needed for warning-free full-lint compilation, not execution.

## Connect progress and cancellation to your server

Analysis checks for cancellation before each step, reports progress after each completed step, and checks once more before returning its result. Invalid arguments fail before any progress callback. The helper does not monitor a network socket: your server observes a disconnect or deadline and signals that call's stop state.

If a progress write fails, keep the failure visible to the caller and stop that computation. Do not continue a disconnected call simply because the callback returned. Cancellation is not a tool argument error and does not require a response on a closed connection.

## Demo controls and exits

Each demo accepts a dataset path, a tool selection, and argument JSON. Analysis also accepts `DELAY_MS` and optional `CANCEL_AFTER`. Cancelling after 3 emits three progress updates and returns no result. Cancelling before the first step or at the final cancellation check also returns no result.

Exit codes are 0 for success, 2 for invalid tool arguments, 3 for cancellation, 4 for invalid argument JSON, and 1 for data/I/O/computation failure. Invalid demo invocation uses 64 in C/Java and argparse's usual 2 in Python. These are demo exit codes, not required student-server exit codes.

## Libraries and licences

The supplied files need no package-manager installation. Keep the relevant licences when including them with your submission.
