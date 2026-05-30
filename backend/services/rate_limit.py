"""
rate_limit.py — protection per-minute par FREK-ID, mémoire process locale.
Pour MVP : sliding window simple. En prod : remplacer par Redis.
"""
from __future__ import annotations

import time
from collections import deque
from threading import Lock

_BUCKETS: dict[str, deque] = {}
_LOCK = Lock()
WINDOW = 60.0  # secondes


def check_and_consume(frek_id: str, limit_per_min: int) -> bool:
    """Retourne True si OK, False si rate-limited."""
    now = time.time()
    cutoff = now - WINDOW
    with _LOCK:
        q = _BUCKETS.get(frek_id)
        if q is None:
            q = deque()
            _BUCKETS[frek_id] = q
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit_per_min:
            return False
        q.append(now)
        return True
