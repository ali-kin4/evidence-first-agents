"""Read-only local workbench plus disposable-fixture remediation simulations.

Never accepts filesystem paths from the browser, never executes discovered commands,
and never makes outbound network connections to configured MCP servers.
"""
from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .demo_cases import catalog
from .remediation import CONTROLS, scenario_report, simulate

ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}
MAX_BODY = 2048


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "EvidenceFirstWorkbench/1.0"

    def log_message(self, format: str, *args: object) -> None:
        # Browser activity and case parameters are not written to console logs.
        return

    def _send(self, status: int, data: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "style-src-attr 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; "
            "form-action 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(data)

    def _json(self, status: int, data: dict | list) -> None:
        self._send(
            status, json.dumps(data, sort_keys=True).encode("utf-8"), "application/json"
        )

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"error": message})

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path in ASSETS:
            asset, media = ASSETS[parsed.path]
            try:
                data = (Path(__file__).with_name("workbench_ui") / asset).read_bytes()
            except OSError:
                self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "UI resource unavailable")
                return
            self._send(HTTPStatus.OK, data, media)
            return
        if parsed.path == "/api/catalog":
            self._json(HTTPStatus.OK, {"scenarios": catalog(), "controls": CONTROLS})
            return
        if parsed.path in ("/api/scenario", "/api/export"):
            query = parse_qs(parsed.query)
            cases = query.get("case", [])
            if len(cases) != 1:
                self._error(HTTPStatus.BAD_REQUEST, "Select exactly one demonstration")
                return
            try:
                result = scenario_report(cases[0])
            except ValueError:
                self._error(HTTPStatus.NOT_FOUND, "Unknown demonstration")
                return
            if parsed.path == "/api/export":
                self._send(
                    HTTPStatus.OK,
                    (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                    "application/json",
                )
            else:
                self._json(HTTPStatus.OK, result)
            return
        self._error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/simulate":
            self._error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return
        origin = self.headers.get("Origin")
        if origin and origin != ("http://" + (self.headers.get("Host") or "")):
            self._error(HTTPStatus.FORBIDDEN, "Cross-origin requests are not allowed")
            return
        if self.headers.get_content_type() != "application/json":
            self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "JSON required")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 2 or length > MAX_BODY:
            self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Invalid body size")
            return
        try:
            raw = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._error(HTTPStatus.BAD_REQUEST, "Malformed JSON body")
            return
        if not isinstance(payload, dict):
            self._error(HTTPStatus.BAD_REQUEST, "JSON object required")
            return
        if set(payload) != {"case", "controls"}:
            self._error(HTTPStatus.BAD_REQUEST, "Unexpected request fields")
            return
        try:
            outcome = simulate(payload["case"], payload["controls"])
        except (ValueError, TypeError):
            self._error(HTTPStatus.BAD_REQUEST, "Unknown scenario or controls")
            return
        self._json(HTTPStatus.OK, outcome)


def serve_workbench(port: int = 8766) -> None:
    if not 1024 <= port <= 65535:
        raise ValueError("Choose a port from 1024 to 65535")
    server = ThreadingHTTPServer(("127.0.0.1", port), WorkbenchHandler)
    server.daemon_threads = True
    print("Evidence First Agents · Authority Workbench")
    print(f"Open http://127.0.0.1:{port}")
    print("Fictional examples only. Local-only server; no agent or MCP execution.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
