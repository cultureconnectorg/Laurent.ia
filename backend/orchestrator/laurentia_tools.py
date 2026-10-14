"""Request-scoped Laurent.ia tools with explicit tenant boundaries."""
from __future__ import annotations

import re
from typing import Any

from .tool_runtime import ToolContext, ToolRegistry, ToolSpec, build_safe_default_registry

_QUERY_MAX = 200
_MAX_SESSIONS = 50
_MAX_MATCHES = 5
_STOP_WORDS = {"avec", "dans", "pour", "mais", "donc", "this", "that", "from", "what", "when"}


def build_request_tool_registry(*, db: Any, frek_id: str, tenant_id: str) -> ToolRegistry:
    """Build a per-request registry; database access is closed over a validated FREK-ID."""
    if not isinstance(frek_id, str) or not frek_id.strip():
        raise ValueError("validated FREK-ID is required")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise ValueError("tenant identity is required")

    registry = build_safe_default_registry()

    def validate_memory_args(arguments: dict[str, Any]) -> bool:
        query = arguments.get("query")
        return (
            set(arguments) == {"query"}
            and isinstance(query, str)
            and 1 <= len(query.strip()) <= _QUERY_MAX
        )

    async def memory_search(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        # The model cannot supply or override frek_id or tenant_id.
        if context.tenant_id != tenant_id:
            raise PermissionError("tenant_scope_mismatch")
        document = await db.laurentia_memory.find_one(
            {"frek_id": frek_id},
            {"_id": 0, "sessions": {"$slice": -_MAX_SESSIONS}},
        )
        sessions = (document or {}).get("sessions", [])
        if not sessions:
            return {"matches": [], "message": "Aucun souvenir enregistré pour cette instance."}

        from services.crypto import decrypt_text

        query_terms = {
            word for word in re.findall(r"[a-zA-ZÀ-ÿ0-9]{3,}", arguments["query"].lower())
            if word not in _STOP_WORDS
        }
        matches = []
        # Newest first; no data from another FREK-ID can enter this candidate set.
        for session in reversed(sessions[-_MAX_SESSIONS:]):
            try:
                user_text = decrypt_text(session.get("input")) or ""
                assistant_text = decrypt_text(session.get("output")) or ""
            except Exception:
                continue
            combined = f"{user_text} {assistant_text}"
            lowered = combined.lower()
            score = sum(1 for term in query_terms if term in lowered)
            if score == 0:
                continue
            matches.append({
                "date": str(session.get("ts") or "")[:32],
                "relevance": score,
                "user_excerpt": user_text[:360],
                "assistant_excerpt": assistant_text[:360],
            })
        matches.sort(key=lambda item: (item["relevance"], item["date"]), reverse=True)
        return {"matches": matches[:_MAX_MATCHES], "searched_sessions": len(sessions)}

    registry.register(ToolSpec(
        name="memory_search",
        description="Recherche dans les échanges mémorisés de cette instance uniquement, sans accéder aux autres tenants.",
        handler=memory_search,
        validate_arguments=validate_memory_args,
        effect="read_only",
        timeout_seconds=2.0,
    ))
    return registry
