# test_sse.py - run with: python test_sse.py
from mcp_io import SSEBuffer

e1 = b'data: {"a":1}\n\n'
e2 = b'data: {"b":2}\n\n'

# 1. A partial event, then the rest plus a whole second event
sse = SSEBuffer()
print(sse.feed(e1[:7]))          # []
print(sse.feed(e1[7:] + e2))     # [{'a': 1}, {'b': 2}]
print(sse.feed(b""))             # []

# 2. The same bytes, one at a time
sse = SSEBuffer()
got = []
for i in range(len(e1 + e2)):
    got += sse.feed((e1 + e2)[i:i + 1])
print(got)                       # [{'a': 1}, {'b': 2}]

# 3. Bad input should raise ValueError
try:
    SSEBuffer().feed(b"data: not json\n\n")
except ValueError as exc:
    print("ValueError:", exc)