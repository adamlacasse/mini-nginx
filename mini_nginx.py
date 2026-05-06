import json
import mimetypes
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


def load_config() -> dict:
    with open("mini-nginx.json", "r", encoding="utf-8") as file:
        return json.load(file)


CONFIG = load_config()

HOST = CONFIG["listen"]["host"]
PORT = CONFIG["listen"]["port"]

PUBLIC_DIR = Path(CONFIG["static"]["root"]).resolve()

PROXY_PREFIX = CONFIG["proxy"]["prefix"]
BACKEND_HOST = CONFIG["proxy"]["target_host"]
BACKEND_PORT = CONFIG["proxy"]["target_port"]


@dataclass
class HttpRequest:
    method: str
    path: str
    version: str
    headers: dict[str, str]
    body: bytes
    raw: bytes


def parse_http_request(request_bytes: bytes) -> HttpRequest:
    header_bytes, _, body = request_bytes.partition(b"\r\n\r\n")

    header_text = header_bytes.decode("iso-8859-1")
    lines = header_text.split("\r\n")

    request_line = lines[0]
    method, path, version = request_line.split(" ", 2)

    headers = {}

    for line in lines[1:]:
        if not line:
            continue

        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()

    return HttpRequest(
        method=method,
        path=path,
        version=version,
        headers=headers,
        body=body,
        raw=request_bytes,
    )


def build_response(
    body: bytes,
    status_code: int = 200,
    reason: str = "OK",
    content_type: str = "text/plain; charset=utf-8",
) -> bytes:
    response_headers = (
        f"HTTP/1.1 {status_code} {reason}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8")

    return response_headers + body


def build_text_response(
    body: str,
    status_code: int = 200,
    reason: str = "OK",
) -> bytes:
    return build_response(
        body.encode("utf-8"),
        status_code,
        reason,
        "text/plain; charset=utf-8",
    )


def safe_join_public(request_path: str) -> Path | None:
    path_without_query = request_path.split("?", 1)[0]
    decoded_path = unquote(path_without_query)

    if decoded_path == "/":
        decoded_path = "/index.html"

    relative_path = decoded_path.lstrip("/")
    candidate_path = (PUBLIC_DIR / relative_path).resolve()

    try:
        candidate_path.relative_to(PUBLIC_DIR)
    except ValueError:
        return None

    return candidate_path


def serve_static_file(request: HttpRequest) -> bytes:
    if request.method != "GET":
        return build_text_response("Method Not Allowed", 405, "Method Not Allowed")

    file_path = safe_join_public(request.path)

    if file_path is None:
        return build_text_response("Forbidden", 403, "Forbidden")

    if not file_path.exists() or not file_path.is_file():
        return build_text_response("Not Found", 404, "Not Found")

    body = file_path.read_bytes()

    content_type, _ = mimetypes.guess_type(str(file_path))

    if content_type is None:
        content_type = "application/octet-stream"

    return build_response(body, 200, "OK", content_type)


def build_proxied_request(request: HttpRequest) -> bytes:
    lines = [
        f"{request.method} {request.path} HTTP/1.1",
        f"Host: {BACKEND_HOST}:{BACKEND_PORT}",
        "Connection: close",
        "X-Forwarded-Proto: http",
    ]

    original_host = request.headers.get("host")
    if original_host:
        lines.append(f"X-Forwarded-Host: {original_host}")

    for header_name in ["user-agent", "accept", "content-type", "content-length"]:
        if header_name in request.headers:
            pretty_name = "-".join(part.capitalize() for part in header_name.split("-"))
            lines.append(f"{pretty_name}: {request.headers[header_name]}")

    header_blob = "\r\n".join(lines).encode("utf-8") + b"\r\n\r\n"

    return header_blob + request.body


def proxy_to_backend(request: HttpRequest) -> bytes:
    try:
        backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        backend_socket.settimeout(5)

        backend_socket.connect((BACKEND_HOST, BACKEND_PORT))

        proxied_request = build_proxied_request(request)
        backend_socket.sendall(proxied_request)

        chunks = []

        while True:
            chunk = backend_socket.recv(4096)

            if not chunk:
                break

            chunks.append(chunk)

        backend_socket.close()

        return b"".join(chunks)

    except ConnectionRefusedError:
        return build_text_response("Bad Gateway: backend is down", 502, "Bad Gateway")

    except TimeoutError:
        return build_text_response("Gateway Timeout", 504, "Gateway Timeout")

    except Exception as err:
        print(f"Proxy error: {err}")
        return build_text_response("Bad Gateway", 502, "Bad Gateway")


def handle_request(request: HttpRequest) -> tuple[bytes, str]:
    if request.path.startswith(PROXY_PREFIX):
        return proxy_to_backend(request), "proxy"

    return serve_static_file(request), "static"


def handle_client(client_socket: socket.socket, client_address: tuple) -> None:
    started_at = time.perf_counter()

    try:
        request_bytes = client_socket.recv(8192)

        if not request_bytes:
            return

        request = parse_http_request(request_bytes)

        response, route_type = handle_request(request)

        elapsed_ms = (time.perf_counter() - started_at) * 1000

        print(
            f"{client_address[0]} "
            f"{request.method} {request.path} "
            f"{route_type} "
            f"{len(response)}B "
            f"{elapsed_ms:.2f}ms"
        )

        client_socket.sendall(response)

    except Exception as err:
        print(f"Error handling request: {err}")
        response = build_text_response(
            "Internal Server Error",
            500,
            "Internal Server Error",
        )
        client_socket.sendall(response)

    finally:
        client_socket.close()


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"MiniNginx listening at http://{HOST}:{PORT}")
    print(f"Serving static files from {PUBLIC_DIR}")
    print(f"Proxying {PROXY_PREFIX}* to http://{BACKEND_HOST}:{BACKEND_PORT}")

    while True:
        client_socket, client_address = server_socket.accept()

        thread = threading.Thread(
            target=handle_client,
            args=(client_socket, client_address),
            daemon=True,
        )

        thread.start()


if __name__ == "__main__":
    main()
