import glob
import json
import os

import server
from student_tools import load_dataset

dataset = load_dataset(server.DATASET_PATH)
EXAMPLES = os.path.join(server.HERE, "..", "..", "examples")
EXPECTED = os.path.join(server.HERE, "..", "..", "expected")


def load(path):
    with open(path) as f:
        return json.load(f)


# 1. Every example request: print status and payload
for path in sorted(glob.glob(os.path.join(EXAMPLES, "*.json"))):
    status, payload = server.handle_request({}, load(path), dataset, 0)
    print(os.path.basename(path), "->", status)
    print("   ", json.dumps(payload)[:160])

# 2. Data comparison against expected/
cases = [("reading.json", "AU01-reading.json"),
         ("history.json", "AU01-history-3.json"),
         ("analysis.json", "AU01-analysis.json")]
for req, exp in cases:
    status, payload = server.handle_request({}, load(os.path.join(EXAMPLES, req)), dataset, 0)
    result = payload["result"]
    got = json.loads(result["content"][0]["text"])
    print(req, "PASS" if got == load(os.path.join(EXPECTED, exp)) else "FAIL")