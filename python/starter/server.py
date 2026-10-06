"""Server entry point. Implement accepting and serving TCP connections here."""

import sys

from app_support import server_options


def main():
    options = server_options()
    print(f"Starter only: server on port {options.port} is not implemented",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
