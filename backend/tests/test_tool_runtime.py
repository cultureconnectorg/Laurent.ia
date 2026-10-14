"""Contract tests for the bounded Laurent.ia tool runtime."""
import asyncio
import json

import pytest

from orchestrator.tool_runtime import (
    ToolContext,
    ToolRegistry,
    ToolRuntimeError,
    ToolSpec,
    build_safe_default_registry,
    parse_tool_proposal,
)

CTX = ToolContext(tenant_id="tenant-test", session_id="session-test", principal_id="user-test")


def test_safe_registry_only_exposes_code_registered_tools():
    registry = build_safe_default_registry()
    assert {tool["name"] for tool in registry.describe()} == {
        "normalize_text", "runtime_capabilities"
    }


def test_normalize_text_is_local_and_bounded():
    registry = build_safe_default_registry()
    result = asyncio.run(registry.execute(
        {"tool": "normalize_text", "arguments": {"text": "  bonjour\n  monde  "}},
        context=CTX,
    ))
    assert result.ok
    assert json.loads(result.output) == {"text": "bonjour monde", "characters": 19}


@pytest.mark.parametrize("proposal", [
    "not json",
    "[]",
    '{"tool":"normalize_text","arguments":{},"shell":"id"}',
    '{"tool":"../../etc/passwd","arguments":{}}',
    '{"tool":"normalize_text","arguments":[]}',
])
def test_malformed_proposals_are_rejected(proposal):
    with pytest.raises(ToolRuntimeError):
        parse_tool_proposal(proposal)


def test_unknown_tool_is_rejected_without_execution():
    registry = build_safe_default_registry()
    result = asyncio.run(registry.execute(
        {"tool": "run_shell", "arguments": {"command": "id"}}, context=CTX
    ))
    assert not result.ok
    assert result.error == "tool_not_allowed"


def test_argument_schema_is_enforced():
    registry = build_safe_default_registry()
    result = asyncio.run(registry.execute(
        {"tool": "normalize_text", "arguments": {"text": "ok", "extra": True}},
        context=CTX,
    ))
    assert not result.ok
    assert result.error == "arguments_invalid"


def test_async_handler_timeout_is_bounded():
    async def slow(context, arguments):
        await asyncio.sleep(0.05)
        return "too late"

    registry = ToolRegistry()
    registry.register(ToolSpec(
        name="slow_tool", description="test timeout", handler=slow,
        validate_arguments=lambda args: args == {}, effect="read_only", timeout_seconds=0.001,
    ))
    result = asyncio.run(registry.execute(
        {"tool": "slow_tool", "arguments": {}}, context=CTX
    ))
    assert not result.ok
    assert result.error == "tool_timeout"


def test_sync_handlers_are_rejected_to_preserve_timeout_cancellation():
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="handlers must be async"):
        registry.register(ToolSpec(
            name="unsafe_sync", description="sync handlers cannot be cancelled",
            handler=lambda context, arguments: "result",
            validate_arguments=lambda args: args == {}, effect="read_only",
        ))


def test_result_is_truncated():
    async def long_result(context, arguments):
        return "x" * 5000

    registry = ToolRegistry()
    registry.register(ToolSpec(
        name="long_result", description="test truncation",
        handler=long_result,
        validate_arguments=lambda args: args == {}, effect="read_only",
    ))
    result = asyncio.run(registry.execute(
        {"tool": "long_result", "arguments": {}}, context=CTX
    ))
    assert result.ok
    assert len(result.output) < 4020
    assert result.output.endswith("…[truncated]")


def test_plan_step_limit_is_enforced():
    registry = ToolRegistry(max_steps=2)
    with pytest.raises(ToolRuntimeError, match="plan_step_limit_exceeded"):
        asyncio.run(registry.execute_plan([{}, {}, {}], context=CTX))


def test_context_requires_trusted_identity_fields():
    with pytest.raises(ToolRuntimeError, match="invalid_context:tenant_id"):
        ToolContext(tenant_id="", session_id="session", principal_id="user")


def test_handler_exception_does_not_leak_details():
    async def secret_failure(context, arguments):
        raise RuntimeError("mongodb://user:secret@example.invalid")

    registry = ToolRegistry()
    registry.register(ToolSpec(
        name="safe_failure", description="test safe error",
        handler=secret_failure, validate_arguments=lambda args: args == {},
    ))
    result = asyncio.run(registry.execute(
        {"tool": "safe_failure", "arguments": {}}, context=CTX
    ))
    assert not result.ok
    assert result.error == "tool_failed"
    assert "secret" not in result.output



def test_side_effecting_tools_are_hidden_and_denied_by_default():
    async def mutate(context, arguments):
        return {"mutated": True}

    registry = ToolRegistry()
    registry.register(ToolSpec(
        name="write_record", description="writes a record", handler=mutate,
        validate_arguments=lambda args: args == {}, effect="write",
    ))
    assert registry.describe() == []
    result = asyncio.run(registry.execute(
        {"tool": "write_record", "arguments": {}}, context=CTX
    ))
    assert not result.ok
    assert result.error == "tool_not_allowed"


def test_unknown_effect_is_denied_by_default():
    async def unclassified(context, arguments):
        return "should never run"

    registry = ToolRegistry()
    registry.register(ToolSpec(
        name="unclassified", description="unclassified tool", handler=unclassified,
        validate_arguments=lambda args: args == {},
    ))
    result = asyncio.run(registry.execute(
        {"tool": "unclassified", "arguments": {}}, context=CTX
    ))
    assert not result.ok
    assert result.error == "tool_not_allowed"
