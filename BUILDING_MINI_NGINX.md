# MiniNginx: A Tiny Reverse Proxy + Static File Server

A learning project that recreates the *shape* of Nginx in a tiny, intentionally simplified way.

You will build:

```txt
Browser
  ↓
MiniNginx written in Python, listening on :8080
  ↓
Either:
  - serve static files from ./public
  - proxy /api/* requests to a Node.js app on :3000
```

The goal is not production readiness. The goal is understanding.

---

## 1. What You Are Building

Your MiniNginx server will:

1. Listen for HTTP requests on `localhost:8080`
2. Parse the basic HTTP request line
3. Route requests by URL path
4. Serve static files from a `public/` directory
5. Proxy `/api/` requests to a Node.js backend
6. Return basic error responses like `404 Not Found` and `502 Bad Gateway`
7. Log each request
8. Eventually handle multiple requests concurrently

Final behavior:

```txt
GET /                  → serve ./public/index.html
GET /style.css         → serve ./public/style.css
GET /api/hello         → proxy to Node.js on localhost:3000
GET /missing           → 404 Not Found
GET /api/whatever      → proxy to Node.js
```

---

## 2. Prerequisites

You need:

```txt
Python 3.10+
Node.js 18+
npm
curl
```

Check versions:

```bash
python3 --version
node --version
npm --version
curl --version
```

---

## 3. Suggested Repo Structure

Create a repo like this:

```txt
mini-nginx/
├── README.md
├── mini_nginx.py
├── mini-nginx.json
├── public/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── node-app/
    ├── package.json
    └── app.js
```

Create it:

```bash
mkdir mini-nginx
cd mini-nginx

mkdir public
mkdir node-app

touch README.md
touch mini_nginx.py
touch mini-nginx.json
touch public/index.html
touch public/style.css
touch public/app.js
touch node-app/app.js
```

---

## 4. Big-Picture Architecture

```txt
Browser
  |
  | GET http://localhost:8080/
  v
MiniNginx Python Server
  |
  | If static route:
  |   read file from ./public
  |
  | If /api route:
  |   open connection to localhost:3000
  |   forward request
  |   read response
  |
  v
Response back to browser
```

For API requests:

```txt
Browser
  ↓
MiniNginx :8080
  ↓
Node.js :3000
  ↓
MiniNginx :8080
  ↓
Browser
```

---

# Phase 1: Build the Node Backend

Start with the backend that MiniNginx will eventually proxy to.

---

## 5. Create the Node App

Inside `node-app/`, initialize a Node project:

```bash
cd node-app
npm init -y
npm install express
cd ..
```

Edit `node-app/app.js`:

```js
const express = require("express");

const app = express();
const PORT = 3000;
const HOST = "127.0.0.1";

app.get("/api/hello", (req, res) => {
  res.json({
    message: "Hello from Node.js",
    path: req.path,
    timestamp: new Date().toISOString()
  });
});

app.get("/api/status", (req, res) => {
  res.json({
    status: "ok",
    service: "node-backend"
  });
});

app.get("/api/echo-headers", (req, res) => {
  res.json({
    headers: req.headers
  });
});

app.use((req, res) => {
  res.status(404).json({
    error: "Not found in Node app",
    path: req.path
  });
});

app.listen(PORT, HOST, () => {
  console.log(`Node app listening at http://${HOST}:${PORT}`);
});
```

Run it:

```bash
cd node-app
node app.js
```

In a second terminal, test it:

```bash
curl http://127.0.0.1:3000/api/hello
curl http://127.0.0.1:3000/api/status
curl http://127.0.0.1:3000/api/echo-headers
```

You should see JSON responses.

Checkpoint:

```txt
Node.js is listening privately on 127.0.0.1:3000.
Eventually, MiniNginx will forward /api/* requests here.
```

---

# Phase 2: Create Static Files

---

## 6. Add a Simple Static Site

Edit `public/index.html`:

```html
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>MiniNginx</title>
    <link rel="stylesheet" href="/style.css" />
  </head>
  <body>
    <main>
      <h1>Hello from MiniNginx</h1>
      <p>This HTML file is served directly by the Python server.</p>

      <button id="load-api">Call Node API through MiniNginx</button>

      <pre id="output">Click the button to call /api/hello</pre>
    </main>

    <script src="/app.js"></script>
  </body>
</html>
```

Edit `public/style.css`:

```css
body {
  font-family: system-ui, sans-serif;
  background: #111;
  color: #eee;
  margin: 0;
  padding: 2rem;
}

main {
  max-width: 720px;
  margin: 0 auto;
}

button {
  font: inherit;
  padding: 0.75rem 1rem;
  cursor: pointer;
}

pre {
  background: #222;
  padding: 1rem;
  overflow: auto;
}
```

Edit `public/app.js`:

```js
const button = document.querySelector("#load-api");
const output = document.querySelector("#output");

button.addEventListener("click", async () => {
  output.textContent = "Loading...";

  try {
    const response = await fetch("/api/hello");
    const data = await response.json();

    output.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    output.textContent = String(err);
  }
});
```

Checkpoint:

```txt
These files will be served by MiniNginx.
The browser will request /, /style.css, and /app.js from Python.
Then /api/hello will be proxied to Node.
```

---

# Phase 3: Build the Simplest Python HTTP Server

---

## 7. Hardcoded HTTP Response

Edit `mini_nginx.py`:

```python
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
```

Run it:

```bash
python3 mini_nginx.py
```

Test it:

```bash
curl http://127.0.0.1:8080/
```

You should see:

```txt
Hello from MiniNginx
```

Checkpoint:

```txt
You now have a tiny web server.
It listens on port 8080, accepts a TCP connection, reads bytes, and sends HTTP bytes back.
```

---

# Phase 4: Parse the Request

---

## 8. Add a Basic Request Parser

Replace `mini_nginx.py` with this version:

```python
import socket
from dataclasses import dataclass


HOST = "127.0.0.1"
PORT = 8080


@dataclass
class HttpRequest:
    method: str
    path: str
    version: str
    headers: dict[str, str]
    body: bytes


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
    )


def build_text_response(
    body: str,
    status_code: int = 200,
    reason: str = "OK",
) -> bytes:
    body_bytes = body.encode("utf-8")

    response_headers = (
        f"HTTP/1.1 {status_code} {reason}\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8")

    return response_headers + body_bytes


def handle_request(request: HttpRequest) -> bytes:
    if request.path == "/":
        return build_text_response("Home page")

    if request.path == "/about":
        return build_text_response("About page")

    if request.path == "/health":
        return build_text_response("OK")

    return build_text_response("Not Found", 404, "Not Found")


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"MiniNginx listening at http://{HOST}:{PORT}")

    while True:
        client_socket, client_address = server_socket.accept()

        try:
            request_bytes = client_socket.recv(4096)
            request = parse_http_request(request_bytes)

            print(f"{client_address} {request.method} {request.path}")

            response = handle_request(request)
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


if __name__ == "__main__":
    main()
```

Test:

```bash
curl http://127.0.0.1:8080/
curl http://127.0.0.1:8080/about
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/nope
```

Checkpoint:

```txt
MiniNginx now parses the request line and routes based on path.
```

---

# Phase 5: Serve Static Files

---

## 9. Add MIME Types and Static File Serving

Replace `mini_nginx.py` with this version:

```python
import mimetypes
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


HOST = "127.0.0.1"
PORT = 8080
PUBLIC_DIR = Path("public").resolve()


@dataclass
class HttpRequest:
    method: str
    path: str
    version: str
    headers: dict[str, str]
    body: bytes


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
    """
    Convert a URL path to a safe filesystem path inside PUBLIC_DIR.

    Prevents path traversal attacks like:
      /../../etc/passwd
    """

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


def handle_request(request: HttpRequest) -> bytes:
    return serve_static_file(request)


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"MiniNginx listening at http://{HOST}:{PORT}")
    print(f"Serving static files from {PUBLIC_DIR}")

    while True:
        client_socket, client_address = server_socket.accept()

        try:
            request_bytes = client_socket.recv(4096)

            if not request_bytes:
                client_socket.close()
                continue

            request = parse_http_request(request_bytes)

            print(f"{client_address} {request.method} {request.path}")

            response = handle_request(request)
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


if __name__ == "__main__":
    main()
```

Run:

```bash
python3 mini_nginx.py
```

Visit:

```txt
http://127.0.0.1:8080/
```

You should see your HTML page with CSS and JavaScript loaded.

Test with curl:

```bash
curl -i http://127.0.0.1:8080/
curl -i http://127.0.0.1:8080/style.css
curl -i http://127.0.0.1:8080/app.js
curl -i http://127.0.0.1:8080/missing
```

Checkpoint:

```txt
MiniNginx is now a static file server.
This is one of Nginx’s core jobs.
```

---

# Phase 6: Add Reverse Proxying

---

## 10. Proxy `/api/` Requests to Node

Now MiniNginx should:

```txt
/api/*    → forward to Node.js on 127.0.0.1:3000
anything else → serve static file
```

Replace `mini_nginx.py` with this version:

```python
import mimetypes
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


HOST = "127.0.0.1"
PORT = 8080
PUBLIC_DIR = Path("public").resolve()

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 3000


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
    """
    Build a simple HTTP/1.1 request to send to the backend.

    This intentionally handles only simple requests.
    """

    lines = [
        f"{request.method} {request.path} HTTP/1.1",
        f"Host: {BACKEND_HOST}:{BACKEND_PORT}",
        "Connection: close",
        "X-Forwarded-Proto: http",
    ]

    original_host = request.headers.get("host")
    if original_host:
        lines.append(f"X-Forwarded-Host: {original_host}")

    # Keep a few simple headers.
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

    except socket.timeout:
        return build_text_response("Gateway Timeout", 504, "Gateway Timeout")

    except Exception as err:
        print(f"Proxy error: {err}")
        return build_text_response("Bad Gateway", 502, "Bad Gateway")


def handle_request(request: HttpRequest) -> tuple[bytes, str]:
    if request.path.startswith("/api/"):
        return proxy_to_backend(request), "proxy"

    return serve_static_file(request), "static"


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"MiniNginx listening at http://{HOST}:{PORT}")
    print(f"Serving static files from {PUBLIC_DIR}")
    print(f"Proxying /api/* to http://{BACKEND_HOST}:{BACKEND_PORT}")

    while True:
        client_socket, client_address = server_socket.accept()

        started_at = time.perf_counter()

        try:
            request_bytes = client_socket.recv(8192)

            if not request_bytes:
                client_socket.close()
                continue

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


if __name__ == "__main__":
    main()
```

Now run both services.

Terminal 1:

```bash
cd node-app
node app.js
```

Terminal 2, from repo root:

```bash
python3 mini_nginx.py
```

Test static files:

```bash
curl -i http://127.0.0.1:8080/
curl -i http://127.0.0.1:8080/style.css
```

Test proxying:

```bash
curl -i http://127.0.0.1:8080/api/hello
curl -i http://127.0.0.1:8080/api/status
curl -i http://127.0.0.1:8080/api/echo-headers
```

Now visit:

```txt
http://127.0.0.1:8080/
```

Click the button.

The browser calls:

```txt
/api/hello
```

But since the browser is talking to MiniNginx on `:8080`, the actual path is:

```txt
Browser → MiniNginx :8080 → Node :3000 → MiniNginx :8080 → Browser
```

Checkpoint:

```txt
You now have a toy reverse proxy.
This is the core Nginx idea.
```

---

# Phase 7: Add a Config File

Right now the routing rules are hardcoded.

Let’s move them into a config file.

---

## 11. Create `mini-nginx.json`

Edit `mini-nginx.json`:

```json
{
  "listen": {
    "host": "127.0.0.1",
    "port": 8080
  },
  "static": {
    "root": "./public"
  },
  "proxy": {
    "prefix": "/api/",
    "target_host": "127.0.0.1",
    "target_port": 3000
  }
}
```

Then update the top of `mini_nginx.py` to load config:

```python
import json
```

Add this near the top:

```python
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
```

Then change this:

```python
if request.path.startswith("/api/"):
```

to this:

```python
if request.path.startswith(PROXY_PREFIX):
```

Checkpoint:

```txt
Your server behavior is now controlled by configuration.
That is very similar in spirit to Nginx.
```

---

# Phase 8: Add Basic Concurrency

Right now MiniNginx handles one request at a time.

A browser often makes several requests quickly:

```txt
GET /
GET /style.css
GET /app.js
GET /favicon.ico
```

Let’s handle each client connection in a separate thread.

---

## 12. Add Thread-Per-Connection Handling

Import threading:

```python
import threading
```

Move your request-handling logic into a function:

```python
def handle_client(client_socket: socket.socket, client_address):
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
```

Then simplify your main loop:

```python
while True:
    client_socket, client_address = server_socket.accept()

    thread = threading.Thread(
        target=handle_client,
        args=(client_socket, client_address),
        daemon=True,
    )

    thread.start()
```

Checkpoint:

```txt
MiniNginx can now handle multiple client connections at the same time.
```

This is not the most scalable model, but it is easy to understand.

Real servers usually use more sophisticated strategies:

```txt
worker processes
thread pools
event loops
non-blocking I/O
epoll/kqueue
```

But thread-per-connection is a good first learning step.

---

# Phase 9: Things to Observe While Testing

Use `curl -i` so you can see headers:

```bash
curl -i http://127.0.0.1:8080/
```

Observe:

```txt
Status line
Headers
Blank line
Body
```

Example:

```http
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 428
Connection: close

<!doctype html>
...
```

Test missing files:

```bash
curl -i http://127.0.0.1:8080/nope
```

Test path traversal protection:

```bash
curl -i http://127.0.0.1:8080/../../etc/passwd
```

You should not get system files back.

Test backend failure:

1. Stop the Node server
2. Run:

```bash
curl -i http://127.0.0.1:8080/api/hello
```

Expected:

```txt
502 Bad Gateway
```

That is exactly the kind of failure a real reverse proxy must handle.

---

# Phase 10: Suggested Final Version Checklist

Your MiniNginx should eventually support:

```txt
[x] Listens on 127.0.0.1:8080
[x] Parses basic HTTP request line
[x] Parses basic headers
[x] Serves static files
[x] Detects MIME types
[x] Prevents path traversal
[x] Proxies /api/* to Node
[x] Returns 404 for missing static files
[x] Returns 502 if backend is down
[x] Logs requests
[x] Uses JSON config
[x] Handles multiple connections with threads
```

---

# Things This Project Intentionally Does Not Handle

This project is educational. It skips many real-world HTTP concerns.

Not supported initially:

```txt
HTTPS/TLS
HTTP/2
HTTP/3
WebSockets
chunked transfer encoding
streaming large files efficiently
range requests
request bodies larger than one recv() call
full keep-alive support
gzip or Brotli compression
cache validation
load balancing
hot config reload
graceful shutdown
advanced security hardening
```

That is fine.

The point is to build the skeleton first.

---

# Recommended Milestones

## Milestone 1

Hardcoded response:

```txt
GET / → Hello from MiniNginx
```

## Milestone 2

Basic routing:

```txt
GET /       → Home page
GET /about  → About page
GET /health → OK
```

## Milestone 3

Static files:

```txt
GET /          → public/index.html
GET /style.css → public/style.css
GET /app.js    → public/app.js
```

## Milestone 4

Reverse proxy:

```txt
GET /api/hello → Node.js backend
```

## Milestone 5

Config:

```txt
mini-nginx.json controls ports, static root, and proxy target
```

## Milestone 6

Concurrency:

```txt
Multiple browser requests can be handled at once
```

---

# Useful Mental Models

## Port

```txt
IP address = which machine
Port       = which program on that machine
```

Example:

```txt
127.0.0.1:8080 → MiniNginx
127.0.0.1:3000 → Node app
127.0.0.1:5432 → PostgreSQL, if you add one later
```

## Listening Socket vs Connected Socket

```txt
listening socket:
  waits for new clients on :8080

connected socket:
  talks to one specific client
```

## Reverse Proxy

```txt
Browser thinks it is talking to one server.

Actually:

Browser → MiniNginx → Node.js
```

MiniNginx hides the backend from the browser.

## Static vs Dynamic

```txt
Static:
  MiniNginx reads file from disk and returns it.

Dynamic:
  MiniNginx forwards request to Node.
  Node runs code and returns response.
```

---

# Extra Credit Ideas

Once the basic version works, consider adding:

## 1. Multiple Proxy Routes

Config:

```json
{
  "routes": [
    {
      "prefix": "/api/",
      "type": "proxy",
      "target_host": "127.0.0.1",
      "target_port": 3000
    },
    {
      "prefix": "/admin/",
      "type": "proxy",
      "target_host": "127.0.0.1",
      "target_port": 4000
    },
    {
      "prefix": "/",
      "type": "static",
      "root": "./public"
    }
  ]
}
```

## 2. Better Logging

Example:

```txt
2026-05-06T12:34:56Z 127.0.0.1 GET /api/hello 200 proxy 42B 5.21ms
```

## 3. Parse Status Code from Backend Response

Right now logging only knows response size. You could parse:

```http
HTTP/1.1 200 OK
```

and extract the `200`.

## 4. Add a Thread Pool

Instead of unbounded threads, use:

```python
from concurrent.futures import ThreadPoolExecutor
```

## 5. Add a Tiny Load Balancer

Proxy `/api/` to multiple backends:

```txt
127.0.0.1:3000
127.0.0.1:3001
127.0.0.1:3002
```

Use round-robin selection.

## 6. Add a Cache

Cache static file contents in memory:

```txt
first request:
  read from disk

next request:
  serve from memory
```

## 7. Add HTTPS Later

Do not start here, but eventually you can explore Python’s `ssl` module.

---

# Development Commands

From repo root:

Start Node backend:

```bash
cd node-app
node app.js
```

Start MiniNginx:

```bash
python3 mini_nginx.py
```

Test static:

```bash
curl -i http://127.0.0.1:8080/
curl -i http://127.0.0.1:8080/style.css
curl -i http://127.0.0.1:8080/app.js
```

Test proxy:

```bash
curl -i http://127.0.0.1:8080/api/hello
curl -i http://127.0.0.1:8080/api/status
curl -i http://127.0.0.1:8080/api/echo-headers
```

Test 404:

```bash
curl -i http://127.0.0.1:8080/nope
```

Test backend down:

```bash
# Stop Node first, then:
curl -i http://127.0.0.1:8080/api/hello
```

---

# Closing Thought

Real Nginx is not magic.

At its core, it does a polished, hardened, extremely efficient version of this:

```txt
listen for requests
match rules
serve files or forward requests
return responses
log what happened
```

Your MiniNginx will be small, naive, and incomplete.

That is exactly why it is valuable.
