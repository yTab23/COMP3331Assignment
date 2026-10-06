"""Read-only computations. The caller owns the dataset and call lifecycle."""

from copy import deepcopy
import json
import math
from pathlib import Path


TOOLS = [
    {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
    }
    for name, description, properties in (
        ("get_reading", "Return the latest fictional reading.", {
            "station_id": {"type": "string"},
        }),
        ("get_history", "Return the latest readings in chronological order.", {
            "station_id": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
        }),
        ("analyse_readings", "Compute the mean of fictional station readings.", {
            "station_id": {"type": "string"},
        }),
    )
]


class Cancelled(Exception):
    """The caller's stop event interrupted an analysis."""


def _reject_constant(value):
    raise ValueError("Nonfinite JSON number: " + value)


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON number is outside the finite float range")
    return number


def parse_json(text):
    """Parse one complete JSON document, rejecting nonfinite numbers."""
    return json.loads(text, parse_constant=_reject_constant, parse_float=_finite_float)


def load_dataset(path):
    """Load and validate once. Arrays are supplied in chronological order."""
    with Path(path).open("rb") as source:
        raw = source.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("Dataset exceeds 1 MiB")
    dataset = parse_json(raw.decode("utf-8"))
    if not isinstance(dataset, dict) or not dataset:
        raise ValueError("Dataset must be a nonempty station object")
    for records in dataset.values():
        if not isinstance(records, list) or not records:
            raise ValueError("Each station needs a nonempty array of readings")
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Each reading must be an object")
            temperature = record.get("temperature_c")
            try:
                valid = type(temperature) in (int, float) and math.isfinite(temperature)
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError("temperature_c must be a finite number, not a boolean")
    return dataset


def _records(dataset, arguments, fields):
    if not isinstance(arguments, dict) or set(arguments) != set(fields):
        raise ValueError("Incorrect tool argument fields")
    station = arguments["station_id"]
    if not isinstance(station, str) or station not in dataset:
        raise ValueError("Unknown station_id")
    return station, dataset[station]


def get_reading(dataset, arguments):
    station, records = _records(dataset, arguments, ["station_id"])
    return {"station_id": station, "reading": deepcopy(records[-1])}


def get_history(dataset, arguments):
    station, records = _records(dataset, arguments, ["station_id", "limit"])
    limit = arguments["limit"]
    if (type(limit) not in (int, float)
            or not 1 <= limit <= 1000 or limit != int(limit)):
        raise ValueError("limit must be an integer from 1 to 1000")
    return {"station_id": station, "readings": deepcopy(records[-int(limit):])}


def analyse_readings(dataset, arguments, step_delay, progress, stop):
    """Call progress(done, total) synchronously; stop is a caller-owned Event."""
    station, records = _records(dataset, arguments, ["station_id"])
    if (type(step_delay) not in (int, float)
            or step_delay < 0 or not math.isfinite(step_delay)):
        raise ValueError("step_delay must be a finite nonnegative number")
    total = 0.0
    for done, record in enumerate(records, 1):
        if stop.wait(step_delay):
            raise Cancelled()
        total += record["temperature_c"]
        progress(done, len(records))
    if stop.is_set():
        raise Cancelled()
    if not math.isfinite(total):
        raise ArithmeticError("Temperature sum is outside the finite float range")
    return {
        "station_id": station,
        "count": len(records),
        "mean_temperature_c": round(total / len(records), 2),
    }
