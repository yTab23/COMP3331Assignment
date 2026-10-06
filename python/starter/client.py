"""Client entry point. Implement socket exchanges and per-call state here."""

import sys

from app_support import client_options
from support.python.student_tools import parse_json


def main():
    options = client_options()
    for line in sys.stdin:
        if not line.strip():
            continue
        command = parse_json(line)
        print(f"Starter only: {command['op']} to {options.host}:{options.port} "
              "is not implemented", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
