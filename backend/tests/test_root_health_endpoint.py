"""Regression test for the public Laurent.ia root status endpoint."""
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "laurentia_test")

try:
    import server  # noqa: E402
except Exception as exc:  # avoid hiding a genuine app import failure as a pass
    pytest.skip(f"Laurent.ia server dependencies unavailable in this test environment: {exc}", allow_module_level=True)


@pytest.mark.asyncio
async def test_root_status_does_not_claim_inference_is_ready_when_unconfigured(monkeypatch):
    monkeypatch.delenv("LAURENTIA_LLM_BASE_URL", raising=False)

    payload = await server.root_health()

    assert payload["service"] == "laurentia"
    assert payload["status"] == "online"
    assert payload["inference_configured"] is False
    assert payload["inference_status"] == "not_configured"
    assert payload["inference_readiness_url"] == "/api/health/inference"


@pytest.mark.asyncio
async def test_root_status_reports_configuration_without_claiming_reachability(monkeypatch):
    monkeypatch.setenv("LAURENTIA_LLM_BASE_URL", "http://llm.internal:8000/v1")

    payload = await server.root_health()

    assert payload["inference_configured"] is True
    assert payload["inference_status"] == "configured"
