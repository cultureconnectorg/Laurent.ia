"""Bounded tool runtime for Laurent.ia.

This module is deliberately separate from the SSE gateway until integration tests
prove the model/tool protocol. Model output is an untrusted *proposal*, never code.
Only tools registered by trusted application code can execute. No shell, eval,
dynamic imports, arbitrary URLs, or model-controlled database queries.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping

_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]{1,47}$")
MAX_ARGUMENT_BYTES = 8_192
MAX_RESULT_CHARS = 4_000
MAX_PLAN_STEPS = 4
DEFAULT_TIMEOUT_SECONDS = 2.0


class ToolRuntimeError(ValueError):
    """A safe, expected rejection of a proposed tool call."""


@dataclass(frozen=True)
class ToolContext:
    """Identity boundary supplied by trusted request middleware, not the model."""
    tenant_id: str
    session_id: str
    principal_id: str

    def __post_init__(self) -> None:
        for name in ("tenant_id", "session_id", "principal_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or len(value) > 256:
                raise ToolRuntimeError(f"invalid_context:{name}")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[[ToolContext, dict[str, Any]], Any]
    validate_arguments: Callable[[dict[str, Any]], bool]
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class ToolResult:
    tool: str
    ok: bool
    output: str
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"tool": self.tool, "ok": self.ok, "output": self.output, "error": self.error}


def _json_size(value: Any) -> int:
    try:
        return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ToolRuntimeError("arguments_not_json_serializable") from exc


def parse_tool_proposal(raw: str | Mapping[str, Any]) -> dict[str, Any]:
    """Parse one strict JSON proposal; reject markdown, extra keys and oversized input."""
    if isinstance(raw, str):
        if len(raw.encode("utf-8")) > MAX_ARGUMENT_BYTES + 1024:
            raise ToolRuntimeError("proposal_too_large")
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ToolRuntimeError("invalid_json") from exc
    elif isinstance(raw, Mapping):
        value = dict(raw)
    else:
        raise ToolRuntimeError("proposal_must_be_object")
    if not isinstance(value, dict) or set(value) != {"tool", "arguments"}:
        raise ToolRuntimeError("proposal_schema_invalid")
    if not isinstance(value["tool"], str) or not _TOOL_NAME.fullmatch(value["tool"]):
        raise ToolRuntimeError("tool_name_invalid")
    if not isinstance(value["arguments"], dict):
        raise ToolRuntimeError("arguments_must_be_object")
    if _json_size(value["arguments"]) > MAX_ARGUMENT_BYTES:
        raise ToolRuntimeError("arguments_too_large")
    return value


class ToolRegistry:
    """Fixed, code-owned allowlist of bounded tool handlers."""

    def __init__(self, *, max_steps: int = MAX_PLAN_STEPS) -> None:
        if not 1 <= max_steps <= MAX_PLAN_STEPS:
            raise ValueError(f"max_steps must be between 1 and {MAX_PLAN_STEPS}")
        self._tools: dict[str, ToolSpec] = {}
        self.max_steps = max_steps

    def register(self, spec: ToolSpec) -> None:
        if not _TOOL_NAME.fullmatch(spec.name):
            raise ValueError("invalid tool name")
        if spec.name in self._tools:
            raise ValueError(f"duplicate tool: {spec.name}")
        if not spec.description.strip() or len(spec.description) > 500:
            raise ValueError("tool description must be 1..500 characters")
        if not 0 < spec.timeout_seconds <= 10:
            raise ValueError("tool timeout must be >0 and <=10 seconds")
        self._tools[spec.name] = spec

    def describe(self) -> list[dict[str, str]]:
        """Safe schema metadata; handlers and internal context are never exposed."""
        return [
            {"name": item.name, "description": item.description}
            for item in self._tools.values()
        ]

    async def execute(
        self, proposal: str | Mapping[str, Any], *, context: ToolContext
    ) -> ToolResult:
        try:
            call = parse_tool_proposal(proposal)
            spec = self._tools.get(call["tool"])
            if spec is None:
                raise ToolRuntimeError("tool_not_allowed")
            if not spec.validate_arguments(call["arguments"]):
                raise ToolRuntimeError("arguments_invalid")
            if inspect.iscoroutinefunction(spec.handler):
                value = await asyncio.wait_for(
                    spec.handler(context, call["arguments"]),
                    timeout=spec.timeout_seconds,
                )
            else:
                # Keep synchronous handlers off the event loop and bound their wait.
                value = await asyncio.wait_for(
                    asyncio.to_thread(spec.handler, context, call["arguments"]),
                    timeout=spec.timeout_seconds,
                )
                if inspect.isawaitable(value):
                    value = await asyncio.wait_for(value, timeout=spec.timeout_seconds)
            output = value if isinstance(value, str) else json.dumps(
                value, ensure_ascii=False, default=str
            )
            if len(output) > MAX_RESULT_CHARS:
                output = output[:MAX_RESULT_CHARS] + "…[truncated]"
            return ToolResult(tool=spec.name, ok=True, output=output)
        except asyncio.TimeoutError:
            return ToolResult(tool=_safe_tool_name(proposal), ok=False, output="", error="tool_timeout")
        except ToolRuntimeError as exc:
            return ToolResult(tool=_safe_tool_name(proposal), ok=False, output="", error=str(exc))
        except Exception:
            # Do not leak stack traces, secrets, provider responses or DB details to the model.
            return ToolResult(tool=_safe_tool_name(proposal), ok=False, output="", error="tool_failed")

    async def execute_plan(
        self, proposals: list[str | Mapping[str, Any]], *, context: ToolContext
    ) -> list[ToolResult]:
        if not isinstance(proposals, list):
            raise ToolRuntimeError("plan_must_be_list")
        if len(proposals) > self.max_steps:
            raise ToolRuntimeError("plan_step_limit_exceeded")
        results: list[ToolResult] = []
        for proposal in proposals:
            results.append(await self.execute(proposal, context=context))
        return results


def _safe_tool_name(proposal: Any) -> str:
    try:
        value = json.loads(proposal) if isinstance(proposal, str) else proposal
        name = value.get("tool", "unknown") if isinstance(value, Mapping) else "unknown"
        return name if isinstance(name, str) and _TOOL_NAME.fullmatch(name) else "unknown"
    except Exception:
        return "unknown"


def _is_text_argument(arguments: dict[str, Any]) -> bool:
    return set(arguments) == {"text"} and isinstance(arguments["text"], str) and len(arguments["text"]) <= 4_000


def _normalize_text(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    # Pure, local utility: no side effects, network, filesystem, or database.
    text = arguments["text"]
    return {"text": " ".join(text.split()), "characters": len(text)}


def _runtime_capabilities(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    if arguments:
        raise ToolRuntimeError("arguments_invalid")
    return {
        "runtime": "laurentia-agentic-runtime",
        "tool_execution": "allowlisted",
        "external_network": False,
        "shell_execution": False,
        "max_plan_steps": MAX_PLAN_STEPS,
    }


def build_safe_default_registry() -> ToolRegistry:
    """Create the initial zero-dependency, no-side-effect tools."""
    registry = ToolRegistry()
    registry.register(ToolSpec(
        name="normalize_text",
        description="Normalise les espaces d'un texte fourni par l'utilisateur (outil local sans effet de bord).",
        handler=_normalize_text,
        validate_arguments=_is_text_argument,
    ))
    registry.register(ToolSpec(
        name="runtime_capabilities",
        description="Décrit les limites de sécurité du moteur d'outils local.",
        handler=_runtime_capabilities,
        validate_arguments=lambda args: args == {},
    ))
    return registry
