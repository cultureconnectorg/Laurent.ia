"""S0 network guard (harness only, outside the repository).
Allows only loopback MongoDB (27017) and the local API (8001); every other
connection or DNS lookup is refused immediately and logged as JSON lines to
$S0_EGRESS_LOG with the first repository frame that triggered it."""
import json, os, socket, traceback, time
_LOG = os.environ.get("S0_EGRESS_LOG")
_ALLOWED_PORTS = {27017, 8001}
_LOCAL = {"localhost", "127.0.0.1", "::1"}
_orig_connect = socket.socket.connect
_orig_gai = socket.getaddrinfo
def _frame():
    for fr in reversed(traceback.extract_stack()[:-2]):
        if "/lia-s0/" in fr.filename:
            return f"{fr.filename.split('/lia-s0/')[1]}:{fr.lineno} ({fr.name})"
    return "?"
def _log(kind, target):
    if _LOG:
        with open(_LOG, "a") as f:
            f.write(json.dumps({"t": time.time(), "pid": os.getpid(), "kind": kind,
                                "target": str(target), "origin": _frame(),
                                "test": os.environ.get("PYTEST_CURRENT_TEST", "")}) + "\n")
def _connect(self, address):
    if self.family == socket.AF_UNIX:
        return _orig_connect(self, address)
    host, port = address[0], address[1]
    if host in _LOCAL and port in _ALLOWED_PORTS:
        return _orig_connect(self, address)
    _log("connect", f"{host}:{port}")
    raise ConnectionRefusedError(f"S0 guard: egress refused to {host}:{port}")
def _gai(host, *a, **k):
    h = host.decode() if isinstance(host, bytes) else host
    if h is None or h in _LOCAL:
        return _orig_gai(host, *a, **k)
    _log("dns", h)
    raise socket.gaierror(socket.EAI_NONAME, f"S0 guard: DNS refused for {h}")
socket.socket.connect = _connect
socket.getaddrinfo = _gai
