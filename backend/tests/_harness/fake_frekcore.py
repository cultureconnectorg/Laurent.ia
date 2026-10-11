"""Minimal FREKCORE stand-in for unit tests (a real local HTTP server).

It accepts every ceremony it is given: tests that use it check what *Laurent.ia*
lets through to FREKCORE (calls are recorded), not WebAuthn itself. The real
FREKCORE is exercised end to end by deploy/verify/passkey_check.py.
"""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeFrekcore:
    def __init__(self):
        self.calls: list[str] = []
        calls = self.calls
        # Test knobs: delay (seconds) or forced status code per path suffix.
        self.delay: dict[str, float] = {}
        self.fail: dict[str, int] = {}
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, body: dict, code: int = 200):
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                calls.append(f"GET {self.path}")
                if self.path.endswith("/status"):
                    self._send({"frek_id": self.path.split("/")[-2], "active": True, "revoked": False})
                else:
                    self._send({"detail": "not found"}, 404)

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                calls.append(f"POST {self.path}")
                for suffix, seconds in fake.delay.items():
                    if self.path.endswith(suffix):
                        time.sleep(seconds)
                for suffix, code in fake.fail.items():
                    if self.path.endswith(suffix):
                        return self._send({"detail": f"forced {code}"}, code)
                if self.path == "/api/v1/auth/token":
                    self._send({"access_token": "fake-token", "expires_in": 3600})
                elif self.path.endswith("/register/begin"):
                    self._send({"challenge": "Y2hhbGxlbmdl", "rp": {"id": "localhost"}, "user": {"id": "dQ", "name": "x"}})
                elif self.path.endswith("/register/complete"):
                    self._send({"ok": True, "holder_verified": True})
                elif self.path.endswith("/authenticate/begin"):
                    self._send({"challenge": "Y2hhbGxlbmdl", "rpId": "localhost", "allowCredentials": []})
                elif self.path.endswith("/authenticate/complete"):
                    self._send({"ok": True})
                else:
                    self._send({"detail": "not found"}, 404)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    def count(self, suffix: str) -> int:
        return sum(1 for c in self.calls if c.endswith(suffix))
