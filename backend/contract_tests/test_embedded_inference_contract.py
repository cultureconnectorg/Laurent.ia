from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]


def test_embedded_model_is_the_default_and_remote_endpoint_is_opt_in():
    source = (BACKEND / "services" / "cvl_brain.py").read_text()
    assert 'os.environ.get("LAURENTIA_INFERENCE_MODE", "embedded")' in source
    assert 'if mode == "embedded"' in source
    assert 'if mode == "controlled-endpoint"' in source
    assert "services.local_inference" in source


def test_runtime_reuses_cached_weights_and_bounds_cpu_memory_work():
    source = (BACKEND / "services" / "local_inference.py").read_text()
    assert "tensorblock/SmolLM2-135M-Instruct-GGUF" in source
    assert "SmolLM2-135M-Instruct-Q2_K.gguf" in source
    assert 'LAURENTIA_MODEL_CACHE", "/tmp/laurentia-model-cache"' in source
    assert "A complete local artifact avoids a Hugging Face request on warm starts." in source
    assert "CONTEXT_TOKENS = max(256, min(768" in source
    assert "CONTEXT_TOKENS - 128" in source
    assert "n_ctx=CONTEXT_TOKENS" in source
    assert "n_threads=THREADS" in source
    assert "n_batch=BATCH_SIZE" in source
    assert "_generation_lock = threading.Lock()" in source
    assert "create_chat_completion" in source
    assert "hf_hub_download" in source
    assert '"cache_hit": _cache_hit' in source
    assert '"load_seconds":' in source
    assert '"last_generation_seconds":' in source
    assert "model.tokenize(system_message.encode" in source
    assert "system_tokens = system_tokens[:system_budget]" in source
    assert "user_tokens = user_tokens[-user_budget:]" in source
    assert "Do not persist prompts or completions in a cache." in source


def test_health_reports_embedded_mode_without_claiming_model_is_ready():
    source = (BACKEND / "server.py").read_text()
    assert 'os.environ.get("LAURENTIA_INFERENCE_MODE", "embedded")' in source
    assert '"model_not_downloaded"' in source
    assert '"model_loaded": status["loaded"]' in source
    assert '"model_downloaded": status["downloaded"]' in source


def test_runtime_is_pinned_to_python_312_and_inference_package_is_declared():
    assert (BACKEND / ".python-version").read_text().strip().startswith("3.12.")
    requirements = (BACKEND / "requirements.txt").read_text()
    assert "llama-cpp-python==" in requirements
