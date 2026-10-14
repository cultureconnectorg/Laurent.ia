"""Tenant isolation tests for request-scoped memory tools."""
import asyncio
import json
from types import SimpleNamespace

from orchestrator.laurentia_tools import build_request_tool_registry
from orchestrator.tool_runtime import ToolContext


class FakeMemoryCollection:
    def __init__(self, document):
        self.document = document
        self.calls = []

    async def find_one(self, query, projection):
        self.calls.append((query, projection))
        return self.document


def test_memory_search_is_scoped_to_validated_frek_id(monkeypatch):
    from services import crypto
    monkeypatch.setattr(crypto, "decrypt_text", lambda value: value or "")
    collection = FakeMemoryCollection({"sessions": [
        {"ts": "2026-10-01", "input": "parle moi du projet Kiltikonet", "output": "Le projet culturel CVLN"},
        {"ts": "2026-10-02", "input": "recette", "output": "gâteau"},
    ]})
    db = SimpleNamespace(laurentia_memory=collection)
    registry = build_request_tool_registry(db=db, frek_id="FREK-VALIDATED-01", tenant_id="tenant-A")
    result = asyncio.run(registry.execute(
        {"tool": "memory_search", "arguments": {"query": "projet Kiltikonet"}},
        context=ToolContext(tenant_id="tenant-A", session_id="session-A", principal_id="user-A"),
    ))
    assert result.ok
    payload = json.loads(result.output)
    assert len(payload["matches"]) == 1
    assert "Kiltikonet" in payload["matches"][0]["user_excerpt"]
    assert collection.calls[0][0] == {"frek_id": "FREK-VALIDATED-01"}
    assert collection.calls[0][1]["sessions"]["$slice"] == -50


def test_memory_search_rejects_tenant_mismatch_before_database_read():
    collection = FakeMemoryCollection({"sessions": []})
    db = SimpleNamespace(laurentia_memory=collection)
    registry = build_request_tool_registry(db=db, frek_id="FREK-VALIDATED-01", tenant_id="tenant-A")
    result = asyncio.run(registry.execute(
        {"tool": "memory_search", "arguments": {"query": "projet"}},
        context=ToolContext(tenant_id="tenant-B", session_id="session-B", principal_id="user-B"),
    ))
    assert not result.ok
    assert result.error == "tool_failed"
    assert collection.calls == []


def test_memory_search_rejects_extra_or_empty_arguments():
    collection = FakeMemoryCollection({"sessions": []})
    registry = build_request_tool_registry(
        db=SimpleNamespace(laurentia_memory=collection),
        frek_id="FREK-VALIDATED-01",
        tenant_id="tenant-A",
    )
    context = ToolContext(tenant_id="tenant-A", session_id="session-A", principal_id="user-A")
    extra = asyncio.run(registry.execute(
        {"tool": "memory_search", "arguments": {"query": "projet", "frek_id": "OTHER"}},
        context=context,
    ))
    empty = asyncio.run(registry.execute(
        {"tool": "memory_search", "arguments": {"query": "  "}},
        context=context,
    ))
    assert extra.error == "arguments_invalid"
    assert empty.error == "arguments_invalid"
    assert collection.calls == []
