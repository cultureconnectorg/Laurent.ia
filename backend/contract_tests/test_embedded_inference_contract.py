from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]


def test_embedded_model_is_the_default_and_remote_endpoint_is_opt_in():
    source = (BACKEND / "services" / "cvl_brain.py").read_text()
    assert 'os.environ.get("LAURENTIA_INFERENCE_MODE", "embedded")' in source
    assert 'if mode == "embedded"' in source
    assert 'if mode == "controlled-endpoint"' in source
    assert "services.local_inference" in source


def test_embedded_runtime_uses_open_weights_and_small_cpu_limits():
    source = (BACKEND / "services" / "local_inference.py").read_text()
    assert "tensorblock/SmolLM2-135M-Instruct-GGUF" in source
    assert "SmolLM2-135M-Instruct-Q2_K.gguf" in source
    assert 'n_ctx=int(os.environ.get("LAURENTIA_LOCAL_CONTEXT", "512"))' in source
    assert 'n_threads=max(1, int(os.environ.get("LAURENTIA_LOCAL_THREADS", "1")))' in source
    assert "create_chat_completion" in source
    assert "hf_hub_download" in source


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
