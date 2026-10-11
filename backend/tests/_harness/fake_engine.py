"""Deterministic local inference engine for tests (S2.2).

A real HTTP server speaking the OpenAI-compatible protocol used by the sovereign
engine (`POST /v1/chat/completions`, streamed or not). It is NOT a model: it
always returns the same fixed answer, so tests check the pipeline (routing,
streaming, persistence, encryption, no egress) — not the answer quality, which
is measured with a real open-weight model in the CI `real-inference` job.

Every request is journaled (JSON lines, `messages` included) so tests can prove
what reached the engine, e.g. that no personal data leaks into a prompt (S3).

Run: python fake_engine.py --port 8090 --log /path/engine.jsonl
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Valid for every caller, including the echo route which requires this JSON schema
# (routes/echo.py ECHO_SYSTEM_PROMPT). Chat routes simply stream it as text.
FIXED_ANSWER = json.dumps({
    "title": "Réponse fixe du moteur local déterministe",
    "summary": "Réponse fixe du moteur de test. Elle ne mesure pas la qualité.",
    "pro": {"headline": "Titre de test", "body": "Corps de test.", "hashtags": ["test", "souverain", "local"]},
    "instant": {"lead": "Accroche de test", "bullets": ["Point un", "Point deux", "Point trois"]},
    "visual": {"punchlines": ["Première phrase de test ici", "Deuxième phrase de test ici",
                              "Troisième phrase de test ici"], "color_hint": "gold"},
}, ensure_ascii=False)


def make_handler(log_path: str | None, calls: list):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep test output clean
            pass

        def _json(self, code: int, body: dict):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                self._json(200, {"status": "ok"})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                self._json(404, {"error": "not found"})
                return
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            entry = {"t": time.time(), "model": body.get("model"), "stream": bool(body.get("stream")),
                     "messages": body.get("messages", [])}
            calls.append(entry)
            if log_path:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            if not body.get("stream"):
                self._json(200, {"choices": [{"index": 0, "message": {"role": "assistant", "content": FIXED_ANSWER},
                                              "finish_reason": "stop"}]})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for i in range(0, len(FIXED_ANSWER), 12):
                chunk = {"choices": [{"index": 0, "delta": {"content": FIXED_ANSWER[i:i + 12]}}]}
                self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    return Handler


class FakeEngine:
    """In-process engine for pytest: `with FakeEngine() as e: e.url, e.calls`."""

    def __init__(self, log_path: str | None = None):
        self.calls: list[dict] = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(log_path, self.calls))
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--log")
    args = ap.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.log, [])).serve_forever()
