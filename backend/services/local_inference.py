"""Embedded CPU inference with bounded concurrency and reusable model cache.

Model weights are open artifacts; prompts are processed in this process and are
never sent to a hosted inference API. Point LAURENTIA_MODEL_CACHE at a persistent
mounted volume when one exists; /tmp is intentionally only an ephemeral fallback.
We deliberately do not persist prompts or completions in a cache.
"""
from __future__ import annotations

import asyncio
import os
import threading
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

MODEL_REPO = os.environ.get(
    "LAURENTIA_LOCAL_MODEL_REPO",
    "tensorblock/SmolLM2-135M-Instruct-GGUF",
)
MODEL_FILE = os.environ.get(
    "LAURENTIA_LOCAL_MODEL_FILE",
    "SmolLM2-135M-Instruct-Q2_K.gguf",
)
MODEL_CACHE = Path(os.environ.get("LAURENTIA_MODEL_CACHE", "/tmp/laurentia-model-cache"))
MODEL_ID = os.environ.get("LAURENTIA_LOCAL_MODEL_ID", "smollm2-135m-instruct-q2_k")
CONTEXT_TOKENS = max(256, min(768, int(os.environ.get("LAURENTIA_LOCAL_CONTEXT", "512"))))
MAX_OUTPUT_TOKENS = max(
    16,
    min(256, CONTEXT_TOKENS - 128, int(os.environ.get("LAURENTIA_LOCAL_MAX_TOKENS", "96"))),
)
THREADS = max(1, min(2, int(os.environ.get("LAURENTIA_LOCAL_THREADS", "1"))))
BATCH_SIZE = max(8, min(32, int(os.environ.get("LAURENTIA_LOCAL_BATCH", "16"))))

_model: Any | None = None
_model_lock = threading.Lock()
_generation_lock = threading.Lock()
_load_seconds: float | None = None
_cache_hit: bool | None = None
_last_generation_seconds: float | None = None
_last_completion_tokens: int | None = None
_generation_count = 0


def model_file_path() -> Path | None:
    """Return a valid cached artifact without making a network request."""
    candidate = MODEL_CACHE / MODEL_FILE
    return candidate if candidate.is_file() and candidate.stat().st_size > 1_000_000 else None


def model_status() -> dict[str, Any]:
    path = model_file_path()
    return {
        "mode": "embedded",
        "model": MODEL_ID,
        "loaded": _model is not None,
        "downloaded": path is not None,
        "artifact": MODEL_FILE if path is not None else None,
        "cache_hit": _cache_hit,
        "load_seconds": round(_load_seconds, 2) if _load_seconds is not None else None,
        "last_generation_seconds": (
            round(_last_generation_seconds, 2)
            if _last_generation_seconds is not None else None
        ),
        "last_completion_tokens": _last_completion_tokens,
        "generation_count": _generation_count,
        "context_tokens": CONTEXT_TOKENS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "generation_busy": _generation_lock.locked(),
    }


def _get_model():
    global _model, _load_seconds, _cache_hit
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        started = time.monotonic()
        MODEL_CACHE.mkdir(parents=True, exist_ok=True)
        cached = model_file_path()
        if cached is not None:
            # A complete local artifact avoids a Hugging Face request on warm starts.
            model_path = str(cached)
            _cache_hit = True
        else:
            from huggingface_hub import hf_hub_download

            model_path = hf_hub_download(
                repo_id=MODEL_REPO,
                filename=MODEL_FILE,
                local_dir=str(MODEL_CACHE),
            )
            _cache_hit = False
        from llama_cpp import Llama

        _model = Llama(
            model_path=model_path,
            n_ctx=CONTEXT_TOKENS,
            n_threads=THREADS,
            n_batch=BATCH_SIZE,
            use_mmap=True,
            use_mlock=False,
            verbose=False,
        )
        _load_seconds = time.monotonic() - started
        return _model


def _messages(model, system_message: str, user_text: str) -> list[dict[str, str]]:
    """Trim by actual model tokens, preserving system instructions and recent user text."""
    prompt_budget = max(96, CONTEXT_TOKENS - MAX_OUTPUT_TOKENS - 32)
    system_budget = min(128, max(48, prompt_budget // 3))
    user_budget = max(32, prompt_budget - system_budget)

    system_tokens = model.tokenize(system_message.encode("utf-8"), add_bos=False, special=False)
    user_tokens = model.tokenize(user_text.encode("utf-8"), add_bos=False, special=False)
    # Preserve the beginning of the system prompt (policy/instructions) and the
    # latest user context. This avoids overflowing n_ctx on long requests.
    if len(system_tokens) > system_budget:
        system_tokens = system_tokens[:system_budget]
    if len(user_tokens) > user_budget:
        user_tokens = user_tokens[-user_budget:]

    system_content = model.detokenize(system_tokens).decode("utf-8", errors="ignore")
    user_content = model.detokenize(user_tokens).decode("utf-8", errors="ignore")
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def _complete(system_message: str, user_text: str) -> str:
    global _last_generation_seconds, _last_completion_tokens, _generation_count
    started = time.monotonic()
    with _generation_lock:
        model = _get_model()
        result = model.create_chat_completion(
            messages=_messages(model, system_message, user_text),
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.2,
        )
    _last_generation_seconds = time.monotonic() - started
    usage = result.get("usage") or {}
    _last_completion_tokens = usage.get("completion_tokens")
    _generation_count += 1
    content = result["choices"][0]["message"].get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Embedded Laurent.ia model returned an empty response.")
    return content.strip()


def _complete_messages(messages: list[dict[str, str]]) -> str:
    """Run a bounded multi-turn transcript through the same local model instance."""
    global _last_generation_seconds, _last_completion_tokens, _generation_count
    started = time.monotonic()
    with _generation_lock:
        model = _get_model()
        prompt_budget = max(96, CONTEXT_TOKENS - MAX_OUTPUT_TOKENS - 32)
        system_budget = min(128, max(48, prompt_budget // 3))
        system = next((item for item in messages if item["role"] == "system"), None)
        system_tokens = (
            model.tokenize(system["content"].encode("utf-8"), add_bos=False, special=False)
            if system else []
        )
        if len(system_tokens) > system_budget:
            system_tokens = system_tokens[:system_budget]
        bounded = []
        if system:
            bounded.append({
                "role": "system",
                "content": model.detokenize(system_tokens).decode("utf-8", errors="ignore"),
            })
        remaining = max(32, prompt_budget - len(system_tokens))
        selected = []
        for item in reversed([item for item in messages if item is not system]):
            content = item["content"]
            tokens = model.tokenize(content.encode("utf-8"), add_bos=False, special=False)
            if len(tokens) > remaining:
                if not selected and remaining > 0:
                    tokens = tokens[-remaining:]
                    selected.append({
                        "role": item["role"],
                        "content": model.detokenize(tokens).decode("utf-8", errors="ignore"),
                    })
                break
            selected.append({"role": item["role"], "content": content})
            remaining -= len(tokens)
            if remaining <= 0:
                break
        bounded.extend(reversed(selected))
        if not bounded:
            raise ValueError("At least one bounded conversation message is required.")
        result = model.create_chat_completion(
            messages=bounded,
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.2,
        )
    _last_generation_seconds = time.monotonic() - started
    usage = result.get("usage") or {}
    _last_completion_tokens = usage.get("completion_tokens")
    _generation_count += 1
    content = result["choices"][0]["message"].get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Embedded Laurent.ia model returned an empty response.")
    return content.strip()


async def chat_messages(messages: list[dict[str, str]]) -> str:
    return await asyncio.to_thread(_complete_messages, messages)


async def chat_complete(system_message: str, user_text: str) -> str:
    return await asyncio.to_thread(_complete, system_message, user_text)


async def chat_stream(system_message: str, user_text: str):
    """Stream generated deltas without blocking the API event loop."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def publish(item):
        loop.call_soon_threadsafe(queue.put_nowait, item)

    def worker():
        global _last_generation_seconds, _last_completion_tokens, _generation_count
        started = time.monotonic()
        try:
            with _generation_lock:
                model = _get_model()
                stream = model.create_chat_completion(
                    messages=_messages(model, system_message, user_text),
                    max_tokens=MAX_OUTPUT_TOKENS,
                    temperature=0.2,
                    stream=True,
                )
                for event in stream:
                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    delta = (choices[0].get("delta") or {}).get("content")
                    if isinstance(delta, str) and delta:
                        publish(("chunk", delta))
            _last_generation_seconds = time.monotonic() - started
            _last_completion_tokens = None
            _generation_count += 1
            publish(("end", None))
        except Exception as exc:
            # Never expose filesystem paths, credentials, or upstream URLs.
            publish(("error", type(exc).__name__))

    threading.Thread(target=worker, name="laurentia-local-inference", daemon=True).start()
    while True:
        kind, payload = await queue.get()
        if kind == "chunk":
            yield payload
        elif kind == "error":
            raise RuntimeError(f"Embedded inference failed ({payload}).")
        else:
            break
