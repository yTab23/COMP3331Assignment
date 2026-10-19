import socket, time
s = socket.socket()
s.bind(("127.0.0.1", 51001))
s.listen()
time.sleep(60)          # accepts connections in the backlog but never reads or replies