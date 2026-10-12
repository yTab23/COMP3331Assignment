import json
from python.starter.student_tools import load_dataset
from server import handle_request

dataset = load_dataset("readings.json")

def load(path):
    with open(path) as f:
        return json.load(f)

cases = [
    ("reading.json",  "AU01-reading.json"),
    ("history.json",  "AU01-history-3.json"),
    ("analysis.json", "AU01-analysis.json"),
]
for req_file, expected_file in cases:
    status, payload = handle_request({}, load("../../examples/" + req_file), dataset, 0)
    got = {k: v for k, v in payload["result"].items() if k != "resultType"}
    print(req_file, status, "PASS" if got == load("../../expected/" + expected_file) else "FAIL")