import socket

HOST = "127.0.0.1"
PORT = 8080


def build_response(body: str) -> bytes:
    body_bytes = body.encode("utf-8")

    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8") + body_bytes

    return response


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"MiniNginx listening at http://{HOST}:{PORT}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Accepted connection from {client_address}")

        request_bytes = client_socket.recv(4096)
        print(request_bytes.decode("utf-8", errors="replace"))

        response = build_response("Hello from MiniNginx")

        client_socket.sendall(response)
        client_socket.close()


if __name__ == "__main__":
    main()
