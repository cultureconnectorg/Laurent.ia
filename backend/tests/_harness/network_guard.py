"""Network guard for tests and for a locally started API (S1.3).

Only loopback and Unix sockets are reachable. Any other connection or DNS
lookup is refused immediately, recorded in ``ATTEMPTS`` and, when
``LAURENTIA_EGRESS_LOG`` is set, appended to that file as JSON lines.
Extra hosts can be allowed with ``LAURENTIA_TEST_ALLOWED_HOSTS``
(comma-separated), e.g. a database service name in CI.
"""
from __future__ import annotations

import json
import os
import socket
import time
import traceback

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
ATTEMPTS: list[dict] = []

_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex
_orig_getaddrinfo = socket.getaddrinfo
_installed = False


def _allowed_hosts() -> set[str]:
    extra = os.environ.get("LAURENTIA_TEST_ALLOWED_HOSTS", "")
    return LOCAL_HOSTS | {h.strip() for h in extra.split(",") if h.strip()}


def _origin() -> str:
    for frame in reversed(traceback.extract_stack()[:-3]):
        if "/backend/" in frame.filename and "_harness" not in frame.filename:
            return f"{frame.filename.split('/backend/')[-1]}:{frame.lineno} ({frame.name})"
    return "?"


def _record(kind: str, target: str) -> None:
    entry = {"t": time.time(), "pid": os.getpid(), "kind": kind, "target": target,
             "origin": _origin(), "test": os.environ.get("PYTEST_CURRENT_TEST", "")}
    ATTEMPTS.append(entry)
    log = os.environ.get("LAURENTIA_EGRESS_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


def _is_local(host: str) -> bool:
    return host in _allowed_hosts() or host.startswith("127.")


def _check(sock: socket.socket, address) -> None:
    if sock.family == getattr(socket, "AF_UNIX", None):
        return
    host, port = address[0], address[1]
    if not _is_local(host):
        _record("connect", f"{host}:{port}")
        raise ConnectionRefusedError(f"network guard: egress refused to {host}:{port}")


def _connect(self, address):
    _check(self, address)
    return _orig_connect(self, address)


def _connect_ex(self, address):
    _check(self, address)
    return _orig_connect_ex(self, address)


def _getaddrinfo(host, *args, **kwargs):
    name = host.decode() if isinstance(host, bytes) else host
    if name is not None and not _is_local(name):
        _record("dns", name)
        raise socket.gaierror(socket.EAI_NONAME, f"network guard: DNS refused for {name}")
    return _orig_getaddrinfo(host, *args, **kwargs)


def install() -> None:
    """Patch socket functions once and drop proxy variables (a local proxy would bypass the guard)."""
    global _installed
    if _installed:
        return
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(var, None)
    socket.socket.connect = _connect
    socket.socket.connect_ex = _connect_ex
    socket.getaddrinfo = _getaddrinfo
    _installed = True
