"""Embedded, CPU-only inference for low-memory Laurent.ia deployments.

The model is downloaded as an open-weight artifact and executed in this process.
Prompts are never sent to a hosted inference API by this adapter.
"""
from __future__ import annotations

import asyncio
import os
import threading
from pathlib import Path
from typing import Any

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

_model: Any | None = None
_model_lock = threading.Lock()
_END = object()


def model_file_path() -> Path | None:
    """Return the model path only if already cached; never performs network I/O."""
    candidate = MODEL_CACHE / MODEL_FILE
    return candidate if candidate.is_file() else None


def model_status() -> dict[str, Any]:
    path = model_file_path()
    return {
        "mode": "embedded",
        "model": MODEL_ID,
        "loaded": _model is not None,
        "downloaded": path is not None,
        "artifact": MODEL_FILE if path is not None else None,
    }


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from huggingface_hub import hf_hub_download
        from llama_cpp import Llama

        MODEL_CACHE.mkdir(parents=True, exist_ok=True)
        path = hf_hub_download(
            repo_id=MODEL_REPO,
            filename=MODEL_FILE,
            local_dir=str(MODEL_CACHE),
        )
        _model = Llama(
            model_path=path,
            n_ctx=int(os.environ.get("LAURENTIA_LOCAL_CONTEXT", "512")),
            n_threads=max(1, int(os.environ.get("LAURENTIA_LOCAL_THREADS", "1"))),
            n_batch=32,
            use_mmap=True,
            use_mlock=False,
            verbose=False,
        )
        return _model


def _messages(system_message: str, user_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_text},
    ]


def _complete(system_message: str, user_text: str) -> str:
    result = _get_model().create_chat_completion(
        messages=_messages(system_message, user_text),
        max_tokens=int(os.environ.get("LAURENTIA_LOCAL_MAX_TOKENS", "160")),
        temperature=0.2,
    )
    content = result["choices"][0]["message"].get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Embedded Laurent.ia model returned an empty response.")
    return content.strip()


async def chat_complete(system_message: str, user_text: str) -> str:
    return await asyncio.to_thread(_complete, system_message, user_text)


async def chat_stream(system_message: str, user_text: str):
    """Stream generated deltas without blocking FastAPI's event loop."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def publish(item):
        loop.call_soon_threadsafe(queue.put_nowait, item)

    def worker():
        try:
            stream = _get_model().create_chat_completion(
                messages=_messages(system_message, user_text),
                max_tokens=int(os.environ.get("LAURENTIA_LOCAL_MAX_TOKENS", "160")),
                temperature=0.2,
                stream=True,
            )
            for event in stream:
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content")
                if isinstance(content, str) and content:
                    publish(("chunk", content))
            publish(("end", None))
        except Exception as exc:
            # Do not expose paths, credentials, or upstream URLs in the client.
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
