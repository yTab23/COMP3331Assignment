# Python support

Standard library only. No installation is needed. Run these commands from the bundle root (`student-resources`):

```sh
python3 -B python/demo.py data/readings.json quick '{"station_id":"AU01"}'
python3 -B python/demo.py data/readings.json history '{"station_id":"AU01","limit":3}'
python3 -B python/demo.py data/readings.json analysis '{"station_id":"AU02"}' 10
python3 -B python/demo.py data/readings.json analysis '{"station_id":"AU01"}' 10 3
```

The last command cancels after three steps, prints no result, and exits with code 3. Analysis accepts optional delay milliseconds (0 to 60000, default 0), then an optional cancellation step (0 to 1000). Progress and errors go to stderr; result JSON goes to stdout. Exit codes are 0 for completion, 1 for data/I/O/computation failure, 2 for invalid arguments or CLI usage, 3 for cancellation, and 4 for invalid argument JSON.

To integrate, import `student_tools` from this directory and load an explicit dataset path once at startup:

```python
import threading
from student_tools import load_dataset, get_reading, get_history, analyse_readings

dataset = load_dataset("/absolute/path/to/data/readings.json")
latest = get_reading(dataset, {"station_id": "AU01"})
history = get_history(dataset, {"station_id": "AU01", "limit": 3})
stop = threading.Event()
result = analyse_readings(dataset, {"station_id": "AU02"}, 0.01,
                          lambda done, total: print(done, total), stop)
```

`load_dataset(path)` reads at most 1 MiB and validates the computation's required structure: a nonempty station object, nonempty reading arrays, and finite numeric `temperature_c` values, excluding booleans. This is not a general JSON Schema validator. Arrays are already chronological; helpers preserve their order. Keep the loaded dataset unchanged while calls use it. Results are independent copies, so changing a returned reading does not change the dataset. There is no import-time file read, global dataset, or implicit working-directory lookup.

`parse_json(text)` parses one complete JSON document. It rejects trailing text, `NaN`, `Infinity`, `-Infinity`, and numbers that overflow a float. Serialization uses `json.dumps(value, allow_nan=False)`. Use unique object member names; Python's JSON parser keeps the last duplicate value.

`TOOLS` contains the three discovery definitions. Tool arguments require exactly the documented fields. History accepts a finite, mathematically integral numeric `limit` from 1 to 1000: `1`, `1.0`, and `1e0` are equivalent. Booleans, strings, and fractional values such as `1.5` are rejected. Limits larger than the available history return all readings. Unknown stations and invalid arguments raise `ValueError`.

The supplied AU01 and AU02 arrays each contain eight samples. Latest readings are sample 8 at 27 C and 17 C respectively. History limit 3 returns samples 6, 7, 8. Analysis returns count 8 and mean temperatures 23.5 C and 13.5 C. It sums sequentially and uses Python `round(mean, 2)`; a nonfinite sum raises `ArithmeticError`.

`analyse_readings(dataset, arguments, step_delay, progress, stop)` waits `step_delay` seconds before each record using the caller's `threading.Event`. It calls `progress(done, total)` after each completed step, on the calling thread. Setting `stop` interrupts waiting and raises `Cancelled`. A final cancellation check also prevents a result if the event was set during the last callback. Callback errors propagate. Invalid arguments fail before progress or waiting. Give each call its own stop event.

The caller owns scheduling, cancellation signals, error mapping, and all socket, HTTP, MCP, and SSE handling. These helpers supply only computation and JSON support.
