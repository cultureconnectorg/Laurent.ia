"""Embedded CPU inference with bounded concurrency and reusable model cache.

Model weights are open artifacts; prompts are processed in this process and are
never sent to a hosted inference API. Point LAURENTIA_MODEL_CACHE at a persistent
mounted volume when one exists; /tmp is intentionally only an ephemeral fallback.
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
MODEL_ID = os.environ.get("LAURENTIA_LLM_MODEL", "smollm2-135m-instruct-q2_k")
CONTEXT_TOKENS = max(256, int(os.environ.get("LAURENTIA_LOCAL_CONTEXT", "512")))
MAX_OUTPUT_TOKENS = max(16, min(256, int(os.environ.get("LAURENTIA_LOCAL_MAX_TOKENS", "96"))))
THREADS = max(1, min(2, int(os.environ.get("LAURENTIA_LOCAL_THREADS", "1"))))
BATCH_SIZE = max(8, min(32, int(os.environ.get("LAURENTIA_LOCAL_BATCH", "16"))))

_model: Any | None = None
_model_lock = threading.Lock()
_generation_lock = threading.Lock()
_load_seconds: float | None = None
_cache_hit: bool | None = None


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


def _messages(system_message: str, user_text: str) -> list[dict[str, str]]:
    # Keep the prompt bounded on a 512-token-class context. Character limits are
    # a safety rail; the model tokenizer remains the final authority on token use.
    system_limit = int(os.environ.get("LAURENTIA_LOCAL_SYSTEM_CHARS", "3000"))
    user_limit = int(os.environ.get("LAURENTIA_LOCAL_INPUT_CHARS", "6000"))
    return [
        {"role": "system", "content": system_message[-system_limit:]},
        {"role": "user", "content": user_text[-user_limit:]},
    ]


def _complete(system_message: str, user_text: str) -> str:
    with _generation_lock:
        result = _get_model().create_chat_completion(
            messages=_messages(system_message, user_text),
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.2,
        )
    content = result["choices"][0]["message"].get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Embedded Laurent.ia model returned an empty response.")
    return content.strip()


async def chat_complete(system_message: str, user_text: str) -> str:
    return await asyncio.to_thread(_complete, system_message, user_text)


async def chat_stream(system_message: str, user_text: str):
    """Stream generated deltas without blocking the API event loop."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def publish(item):
        loop.call_soon_threadsafe(queue.put_nowait, item)

    def worker():
        try:
            with _generation_lock:
                stream = _get_model().create_chat_completion(
                    messages=_messages(system_message, user_text),
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
