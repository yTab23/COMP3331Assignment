import json
from server import wants_stream

def load(name):
    with open("../../examples/" + name) as f:
        return json.load(f)

print(wants_stream(load("analysis.json")))   # True: analyse_readings with token p5
print(wants_stream(load("reading.json")))    # False: quick tool
print(wants_stream(load("discover.json")))   # False: not tools/call