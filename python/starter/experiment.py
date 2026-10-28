import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT = os.path.join(HERE, "client.py")
SERVER = os.path.join(HERE, "server.py")

WAIT = json.dumps({"op": "wait"})


def call(name, arguments):
    return json.dumps({"op": "call", "name": name, "arguments": arguments})


FOUR_CALLS = [
    call("analyse_readings", {"station_id": "AU01"}),
    call("analyse_readings", {"station_id": "AU02"}),
    call("get_reading", {"station_id": "AU01"}),
    call("get_reading", {"station_id": "AU02"}),
]
SEQUENTIAL = [line for c in FOUR_CALLS for line in (c, WAIT)]   # a wait after every call
CONCURRENT = FOUR_CALLS + [WAIT]                                # all calls, then one wait
ONE_SLOW = [call("analyse_readings", {"station_id": "AU01"}), WAIT]


class Server:
    """Runs server.py as a subprocess and reads its stderr log."""

    def __init__(self, port, delay):
        self.lines = []
        self.ready = threading.Event()
        self.proc = subprocess.Popen(
            [sys.executable, SERVER, "--port", str(port), "--analysis-delay", str(delay)],
            stderr=subprocess.PIPE, text=True, cwd=HERE)
        threading.Thread(target=self._pump, daemon=True).start()
        if not self.ready.wait(10):
            raise SystemExit("server did not start (is the port already in use?)")

    def _pump(self):
        for line in self.proc.stderr:
            line = line.rstrip()
            self.lines.append(line)
            if line.startswith("Listening"):
                self.ready.set()

    def accepted(self):
        return sum(1 for l in self.lines if l.startswith("accepted"))

    def problems(self):
        return [l for l in self.lines if "Traceback" in l or l.startswith("connection dropped")]

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def run_client(port, timeout, lines, results, index):
    expected = sum(1 for l in lines if json.loads(l)["op"] == "call")
    outcomes = Counter()
    had_stderr = False
    try:
        proc = subprocess.Popen(
            [sys.executable, CLIENT, "--port", str(port), "--timeout", str(timeout)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=HERE)
        try:
            out, err = proc.communicate("\n".join(lines) + "\n", timeout=timeout + 30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
        had_stderr = bool(err.strip())
        for line in out.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("event") == "finished":
                outcomes[event.get("outcome")] += 1
    except Exception as exc:
        print("harness error:", exc, file=sys.stderr)
        had_stderr = True
    results[index] = (outcomes, expected, had_stderr)


def run_batch(port, timeout, batch):
    """Start one client process per entry in `batch` together; return the totals."""
    results = [None] * len(batch)
    threads = [threading.Thread(target=run_client, args=(port, timeout, lines, results, i))
               for i, lines in enumerate(batch)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - start          # first start until every client has exited
    outcomes, expected, with_stderr = Counter(), 0, 0
    for got, exp, had_stderr in results:
        outcomes.update(got)
        expected += exp
        with_stderr += had_stderr
    completed = outcomes["success"]
    return elapsed, completed, expected - completed, outcomes, with_stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=51234)    # not 51000, so a manual server doesn't clash
    ap.add_argument("--delay", type=float, default=0.1)
    ap.add_argument("--timeout", type=float, default=30)
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()

    server = Server(args.port, args.delay)
    try:
        print("Environment:", platform.platform(), "| Python", platform.python_version())
        print("analysis-delay %.2f s/step | client timeout %.0f s | connection reuse: on | repeats: %d"
              % (args.delay, args.timeout, args.repeats))

        run_batch(args.port, args.timeout, [[call("get_reading", {"station_id": "AU01"}), WAIT]])  # warm-up

        print("\nSequential vs concurrent (one client process, same four calls)")
        print("%-12s %-4s %-10s %-9s %-7s %s" % ("run", "#", "elapsed s", "completed", "failed", "connections opened"))
        for label, lines in (("sequential", SEQUENTIAL), ("concurrent", CONCURRENT)):
            times = []
            for r in range(1, args.repeats + 1):
                before = server.accepted()
                elapsed, ok, bad, _, _ = run_batch(args.port, args.timeout, [lines])
                time.sleep(0.3)                                    # let the server log its last lines
                times.append(elapsed)
                print("%-12s %-4d %-10.2f %-9d %-7d %d" % (label, r, elapsed, ok, bad, server.accepted() - before))
            print("%-12s median %.2f s" % (label, statistics.median(times)))

        print("\nIndependent clients (one slow analyse_readings call each, then wait)")
        print("%-8s %-10s %-7s %-10s %s" % ("clients", "completed", "failed", "elapsed s", "notes"))
        for n in (1, 4, 8, 16):
            before = server.accepted()
            elapsed, ok, bad, outcomes, with_stderr = run_batch(args.port, args.timeout, [ONE_SLOW] * n)
            time.sleep(0.3)
            notes = "connections %d" % (server.accepted() - before)
            if bad:
                notes += " | outcomes " + str(dict(outcomes))
            if with_stderr:
                notes += " | %d client(s) wrote to stderr" % with_stderr
            print("%-8d %-10d %-7d %-10.2f %s" % (n, ok, bad, elapsed, notes))

        problems = server.problems()
        print("\nServer log: %d dropped/traceback line(s)" % len(problems))
        for line in problems[:5]:
            print("  ", line)
    finally:
        server.stop()


if __name__ == "__main__":
    main()