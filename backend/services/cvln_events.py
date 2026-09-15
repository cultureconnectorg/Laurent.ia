"""
cvln_events.py — Laurentia -> Meta CVLN event emission (Event v1.0).

Laurentia keeps its own internal orchestrator bus (`orchestrator/event_bus.py`)
untouched. This module is the *estate-facing* edge: it emits Event v1.0
envelopes to Meta CVLN's signed bus (`POST /api/events/emit`), which is the
authority layer's own, already-implemented contract surface.

Design rules (PATCH-007):
  * Best effort, never blocking. A user-facing request never fails because the
    authority layer is unreachable — emission failures are recorded, not raised.
  * No silent invention: if `CVLN_META_URL` is unset the emitter reports
    `skipped:not_configured`. It does not pretend to have delivered anything.
  * Every emission carries a trace_id so a request can be followed across
    Laurentia -> Agent Factory -> Meta CVLN.

KNOWN GAP (recorded, not worked around): Meta CVLN's `/api/events/emit`
authenticates with `get_current_user`, i.e. a **human user's JWT**. There is no
service-account / machine identity in the audited MetaCVLN repo. Laurentia
therefore sends whatever bearer token it is given in `CVLN_META_TOKEN`; issuing
a machine token is Meta CVLN-side work and stays OPEN in the estate's
connection registry.
"""
from __future__ import annotations

import os
from collections import deque
from typing import Any, Deque, Dict, List, Optional

import httpx

from services.cvln_contracts import Event, new_trace_id

META_URL = os.environ.get("CVLN_META_URL", "").rstrip("/")
META_TOKEN = os.environ.get("CVLN_META_TOKEN", "")
EMIT_TIMEOUT_S = float(os.environ.get("CVLN_EMIT_TIMEOUT_S", "3.0"))

# Local observability journal: the last N emissions with their delivery status.
_JOURNAL_MAX = int(os.environ.get("CVLN_EVENT_JOURNAL_MAX", "200"))
_journal: Deque[Dict[str, Any]] = deque(maxlen=_JOURNAL_MAX)


def build_event(
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
    priority: int = 3,
) -> Event:
    return Event(
        trace_id=trace_id or new_trace_id(),
        type=event_type,
        payload=payload or {},
        subject_type=subject_type,
        subject_id=subject_id,
        priority=priority,
    )


def _record(event: Event, status: str, detail: Optional[str] = None, http: Optional[int] = None) -> Dict[str, Any]:
    entry = {
        "event_id": event.id,
        "trace_id": event.trace_id,
        "type": event.type,
        "status": status,
        "http": http,
        "detail": detail,
        "timestamp": event.timestamp,
    }
    _journal.append(entry)
    return entry


async def emit(event: Event) -> Dict[str, Any]:
    """Emit one Event v1.0 to Meta CVLN. Never raises."""
    if not META_URL:
        return _record(event, "skipped", "CVLN_META_URL not configured")

    headers = {"Content-Type": "application/json", "X-CVLN-Trace-Id": event.trace_id}
    if META_TOKEN:
        headers["Authorization"] = f"Bearer {META_TOKEN}"

    url = f"{META_URL}/api/events/emit"
    try:
        async with httpx.AsyncClient(timeout=EMIT_TIMEOUT_S) as client:
            resp = await client.post(url, json=event.model_dump(), headers=headers)
        if resp.status_code < 400:
            return _record(event, "delivered", None, resp.status_code)
        return _record(event, "rejected", resp.text[:200], resp.status_code)
    except Exception as exc:  # network, DNS, timeout — recorded, never raised
        return _record(event, "failed", f"{type(exc).__name__}: {str(exc)[:160]}")


async def emit_type(
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Convenience: build + emit in one call."""
    return await emit(build_event(event_type, payload=payload, trace_id=trace_id, **kwargs))


def recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Local observability: the most recent emissions and their delivery status."""
    items = list(_journal)
    return items[-limit:][::-1]


def journal_stats() -> Dict[str, Any]:
    items = list(_journal)
    by_status: Dict[str, int] = {}
    for it in items:
        by_status[it["status"]] = by_status.get(it["status"], 0) + 1
    return {
        "configured": bool(META_URL),
        "meta_url": META_URL or None,
        "authenticated": bool(META_TOKEN),
        "total": len(items),
        "by_status": by_status,
    }


def _reset_journal_for_tests() -> None:
    _journal.clear()
