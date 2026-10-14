"""Tests for the bounded model -> tool -> model loop."""
import asyncio
import json

import pytest

from orchestrator.agent_loop import TOOL_CLOSE, TOOL_OPEN, run_agent_turn
from orchestrator.tool_runtime import (
    ToolContext, ToolRegistry, ToolRuntimeError, build_safe_default_registry,
)

CTX = ToolContext(tenant_id="tenant-test", session_id="session-test", principal_id="user-test")


def envelope(tool, arguments):
    return TOOL_OPEN + json.dumps({"tool": tool, "arguments": arguments}) + TOOL_CLOSE


def test_model_tool_model_loop_executes_allowlisted_tool_then_returns_answer():
    calls = []

    async def model(messages, tools):
        calls.append((messages[:], tools[:]))
        if len(calls) == 1:
            return envelope("normalize_text", {"text": "  bonjour   monde "})
        assert messages[-1]["role"] == "user"
        assert "bonjour monde" in messages[-1]["content"]
        assert "données non fiables" in messages[-1]["content"]
        return "Texte normalisé : bonjour monde."

    result = asyncio.run(run_agent_turn(
        user_text="Nettoie ce texte", system_message="Tu es Laurent.ia.",
        model_turn=model, registry=build_safe_default_registry(), context=CTX,
    ))
    assert result.answer == "Texte normalisé : bonjour monde."
    assert result.tool_calls == 1
    assert result.stopped_reason == "final_answer"
    assert len(calls) == 2


def test_model_cannot_execute_unknown_tool():
    async def model(messages, tools):
        if not any("Résultat d’outil" in m["content"] for m in messages):
            return envelope("shell", {"command": "id"})
        return "Action refusée."

    result = asyncio.run(run_agent_turn(
        user_text="Lance une commande", system_message="safe",
        model_turn=model, registry=build_safe_default_registry(), context=CTX,
    ))
    assert result.tool_results[0].error == "tool_not_allowed"
    assert result.answer == "Action refusée."


def test_tool_call_budget_stops_loop():
    async def model(messages, tools):
        return envelope("normalize_text", {"text": "hello"})

    result = asyncio.run(run_agent_turn(
        user_text="hello", system_message="safe", model_turn=model,
        registry=build_safe_default_registry(), context=CTX, max_tool_calls=1,
    ))
    assert result.tool_calls == 1
    assert result.stopped_reason == "tool_call_budget_exceeded"


def test_invalid_tool_envelope_is_rejected():
    async def model(messages, tools):
        return TOOL_OPEN + '{"tool":'  # no close marker

    with pytest.raises(ToolRuntimeError, match="tool_envelope_incomplete"):
        asyncio.run(run_agent_turn(
            user_text="hello", system_message="safe", model_turn=model,
            registry=build_safe_default_registry(), context=CTX,
        ))


def test_model_timeout_is_bounded():
    async def model(messages, tools):
        await asyncio.sleep(0.05)
        return "late"

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(run_agent_turn(
            user_text="hello", system_message="safe", model_turn=model,
            registry=build_safe_default_registry(), context=CTX,
            model_timeout_seconds=0.001,
        ))

def test_request_approved_effect_is_exposed_to_model_but_not_without_approval():
    from orchestrator.tool_runtime import ToolSpec

    async def write_record(context, arguments):
        return {"written": True}

    registry = ToolRegistry(allowed_effects={"read_only", "write"})
    registry.register(ToolSpec(
        name="write_record",
        description="Écrit un enregistrement après autorisation explicite.",
        handler=write_record,
        validate_arguments=lambda args: args == {},
        effect="write",
    ))
    captured = {}

    async def model(messages, tools):
        captured["tools"] = tools
        return "Terminé."

    default_context = CTX
    asyncio.run(run_agent_turn(
        user_text="test", system_message="safe", model_turn=model,
        registry=registry, context=default_context,
    ))
    assert captured["tools"] == []

    approved_context = ToolContext(
        tenant_id="tenant-test",
        session_id="session-test",
        principal_id="user-test",
        approved_effects=frozenset({"read_only", "write"}),
    )
    asyncio.run(run_agent_turn(
        user_text="test", system_message="safe", model_turn=model,
        registry=registry, context=approved_context,
    ))
    assert captured["tools"] == [
        {"name": "write_record", "description": "Écrit un enregistrement après autorisation explicite."}
    ]
