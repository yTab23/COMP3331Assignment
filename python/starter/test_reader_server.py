import socket
from mcp_io import Connection

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 51000))
    server.listen(1)
    print("Listening on 127.0.0.1:51000...")

    sock, addr = server.accept()
    conn = Connection(sock)
    while True:
        result = conn.read_message()
        if result is None:
            print("Client closed the connection")
            break
        headers, body = result
        print("HEADERS:", headers)
        print("BODY:", body)
    sock.close()

if __name__ == "__main__":
    main()
