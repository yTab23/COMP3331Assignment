
import sys
import socket
import json
import threading


def handle(conn):
    header, body = processRequest(conn)
    print("HEADERS:", header)
    print("BODY:", body)


def processRequest(serverSocket):
    ## keep a bytearray buffer
    buffer = bytearray()
    # get all data chunks

    #Phase A
    while True:
        data = serverSocket.recv(1024)
        if data == b'':
            break

        buffer.extend(data)
        if b"\r\n\r\n" in buffer:
            break

    #Phase B
    #Add all chunks into one big batch then decode:
    request = buffer.decode('utf-8')
    header = {}

    parts = request.split('\r\n')
    for line in parts:
        if ": " in line:
            name, value = line.split(": ")
            header[name] = value

    ContentLength = int(header["Content-Length"])
    # Phase 3
    # With the bytes for the header collected, it is now time to
    # receive bytes again and collect the body.

    header_end = buffer.index(b"\r\n\r\n") + 4
    body_so_far = buffer[header_end:]

    while len(body_so_far) < ContentLength:
        data = serverSocket.recv(1024)
        if data == b'':
            break
        body_so_far += data

    body = json.loads(body_so_far.decode('utf-8'))

    return (header , body)

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 51000))
    server.listen(1)
    print("Listening on 127.0.0.1:51000...")
    conn, addr = server.accept()
    handle(conn)

if __name__ == "__main__":
    main()




