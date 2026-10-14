"""Bounded model/tool/model loop for Laurent.ia.

The model only emits a strict, explicitly delimited JSON proposal. All execution
remains inside ToolRegistry's code-owned allowlist. This module is framework and
provider agnostic; callers choose when/how to expose it to a request.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Awaitable, Callable, Mapping, Any

from .tool_runtime import ToolContext, ToolRegistry, ToolResult, ToolRuntimeError

TOOL_OPEN = "[[TOOL_CALL]]"
TOOL_CLOSE = "[[/TOOL_CALL]]"
MAX_MODEL_REPLY_CHARS = 12_000
MAX_TOOL_HISTORY = 8


@dataclass(frozen=True)
class AgentTurnResult:
    answer: str
    tool_calls: int
    tool_results: tuple[ToolResult, ...]
    stopped_reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "tool_calls": self.tool_calls,
            "tool_results": [result.as_dict() for result in self.tool_results],
            "stopped_reason": self.stopped_reason,
        }


ModelTurn = Callable[[list[dict[str, str]], list[dict[str, str]]], Awaitable[str]]


def _extract_proposal(reply: str) -> str | None:
    """Return a proposal only if the entire model response is a tool envelope."""
    if not isinstance(reply, str) or len(reply) > MAX_MODEL_REPLY_CHARS:
        raise ToolRuntimeError("model_reply_invalid_or_too_large")
    stripped = reply.strip()
    if not stripped.startswith(TOOL_OPEN):
        return None
    if not stripped.endswith(TOOL_CLOSE):
        raise ToolRuntimeError("tool_envelope_incomplete")
    payload = stripped[len(TOOL_OPEN):-len(TOOL_CLOSE)].strip()
    if not payload:
        raise ToolRuntimeError("tool_envelope_empty")
    return payload


async def run_agent_turn(
    *,
    user_text: str,
    system_message: str,
    model_turn: ModelTurn,
    registry: ToolRegistry,
    context: ToolContext,
    max_tool_calls: int = 3,
    model_timeout_seconds: float = 30.0,
) -> AgentTurnResult:
    """Run a bounded reasoning/action loop and return a final user-facing answer.

    The model callback receives messages and safe tool descriptions, and returns
    one complete response. It must not execute tools itself. A normal response is
    final; an enveloped response is validated and dispatched to the allowlist.
    """
    if not isinstance(user_text, str) or not user_text.strip():
        raise ToolRuntimeError("user_text_required")
    if not isinstance(system_message, str) or len(system_message) > 40_000:
        raise ToolRuntimeError("system_message_invalid")
    if not 0 <= max_tool_calls <= registry.max_steps:
        raise ToolRuntimeError("tool_call_budget_invalid")
    if not 0 < model_timeout_seconds <= 60:
        raise ToolRuntimeError("model_timeout_invalid")

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_text},
    ]
    descriptions = registry.describe()
    results: list[ToolResult] = []
    tool_calls = 0

    while True:
        reply = await asyncio.wait_for(
            model_turn(messages, descriptions), timeout=model_timeout_seconds
        )
        proposal = _extract_proposal(reply)
        if proposal is None:
            answer = reply.strip()
            if not answer:
                raise ToolRuntimeError("model_answer_empty")
            return AgentTurnResult(
                answer=answer,
                tool_calls=tool_calls,
                tool_results=tuple(results),
                stopped_reason="final_answer",
            )

        messages.append({"role": "assistant", "content": reply})
        if tool_calls >= max_tool_calls:
            messages.append({
                "role": "tool",
                "content": json.dumps(
                    {"ok": False, "error": "tool_call_budget_exceeded"},
                    separators=(",", ":"),
                ),
            })
            return AgentTurnResult(
                answer="Je n’ai pas pu terminer cette action dans le budget d’outils autorisé. Reformule la demande ou réduis le périmètre.",
                tool_calls=tool_calls,
                tool_results=tuple(results),
                stopped_reason="tool_call_budget_exceeded",
            )

        tool_calls += 1
        try:
            result = await registry.execute(proposal, context=context)
        except ToolRuntimeError as exc:
            result = ToolResult(tool="unknown", ok=False, output="", error=str(exc))
        results.append(result)
        messages.append({
            "role": "tool",
            "content": json.dumps(result.as_dict(), ensure_ascii=False, separators=(",", ":"))[:4_500],
        })
        # Prevent unbounded transcript growth if a caller configures a larger budget.
        if len(results) > MAX_TOOL_HISTORY:
            return AgentTurnResult(
                answer="La limite de sécurité du moteur d’outils a été atteinte.",
                tool_calls=tool_calls,
                tool_results=tuple(results),
                stopped_reason="tool_history_limit",
            )
