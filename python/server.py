"""Local simulation API. Run python3 python/server.py (127.0.0.1:8000)."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from socket import timeout as SocketTimeout
from urllib.parse import urlsplit

from electoral import ElectionError, METHODS, reject_constant, simulate
from multi_winner import ElectionError as MultiElectionError
from multi_winner import METHODS as MULTI_METHODS, simulate as simulate_multi

MAX_BYTES = 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    body_timeout = 10

    def send_json(self, status, data):
        encoded = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if urlsplit(self.path).path == "/systems":
            self.send_json(200, {"methods": list(METHODS)})
        elif urlsplit(self.path).path == "/multi/systems":
            self.send_json(200, {"methods": list(MULTI_METHODS)})
        else:
            self.send_json(404, {"error": "Unknown endpoint"})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in {"/simulate", "/multi/simulate"}:
            self.send_json(404, {"error": "Unknown endpoint"})
            return
        try:
            if self.headers.get("Transfer-Encoding"):
                raise ElectionError("Transfer-Encoding is not supported")
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                raise ElectionError("Content-Length must be an integer")
            if length < 0:
                raise ElectionError("Content-Length is required")
            if length > MAX_BYTES:
                raise ElectionError("Request body exceeds 1 MiB", 413)
            if self.headers.get_content_type() != "application/json":
                raise ElectionError("Content-Type must be application/json", 415)
            self.connection.settimeout(self.body_timeout)
            body = self.rfile.read(length)
            if len(body) != length:
                raise ElectionError("Incomplete request body")
            try:
                request = json.loads(body.decode("utf-8"), parse_constant=reject_constant)
            except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
                raise ElectionError("Request must be valid UTF-8 JSON")
            counter = simulate_multi if path == "/multi/simulate" else simulate
            self.send_json(200, counter(request))
        except (ElectionError, MultiElectionError) as error:
            self.send_json(error.status, {"error": str(error)})
        except (TimeoutError, SocketTimeout):
            self.send_json(408, {"error": "Request body timed out"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print("Simulation API on http://127.0.0.1:" + str(server.server_port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
