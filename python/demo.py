"""Local JSON parse, computation, and serialization demo. No networking."""

import argparse
import json
import sys
import threading

from student_tools import Cancelled, analyse_readings, get_history, get_reading
from student_tools import load_dataset, parse_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help="path to data/readings.json")
    parser.add_argument("operation", choices=("quick", "history", "analysis"))
    parser.add_argument("arguments", help="one JSON tool-arguments object")
    parser.add_argument("delay_ms", nargs="?", type=int)
    parser.add_argument("cancel_after", nargs="?", type=int)
    args = parser.parse_args()
    if args.operation != "analysis" and args.delay_ms is not None:
        parser.error("delay and cancellation apply only to analysis")
    if args.delay_ms is not None and not 0 <= args.delay_ms <= 60000:
        parser.error("delay_ms must be from 0 to 60000")
    if args.cancel_after is not None and not 0 <= args.cancel_after <= 1000:
        parser.error("cancel_after must be from 0 to 1000")
    try:
        dataset = load_dataset(args.dataset)
    except (OSError, ValueError) as error:
        print("Dataset: " + str(error), file=sys.stderr)
        return 1
    try:
        arguments = parse_json(args.arguments)
    except ValueError as error:
        print("JSON: " + str(error), file=sys.stderr)
        return 4

    stop = threading.Event()
    if args.cancel_after == 0:
        stop.set()

    def progress(done, total):
        print(f"progress {done}/{total}", file=sys.stderr, flush=True)
        if args.cancel_after is not None and done >= args.cancel_after:
            stop.set()

    try:
        if args.operation == "quick":
            result = get_reading(dataset, arguments)
        elif args.operation == "history":
            result = get_history(dataset, arguments)
        else:
            result = analyse_readings(
                dataset, arguments, (args.delay_ms or 0) / 1000, progress, stop,
            )
        print(json.dumps(result, allow_nan=False), flush=True)
    except Cancelled:
        print("Cancelled", file=sys.stderr)
        return 3
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (ArithmeticError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
