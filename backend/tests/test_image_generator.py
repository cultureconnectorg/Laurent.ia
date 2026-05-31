"""
test_image_generator.py — Chantier 7 image_generator.py
"""
import os
import asyncio
import pytest


def _reload_module(env: dict):
    """Reload image_generator avec env donné pour tester les branches."""
    for k, v in env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    import importlib
    from services import image_generator as ig
    importlib.reload(ig)
    return ig


def test_style_prefix_known_and_unknown():
    ig = _reload_module({})
    assert "Caribbean mystical" in ig.style_prefix("vision")
    assert "Martinique" in ig.style_prefix("culture")
    assert "sovereign AI" in ig.style_prefix("feature")
    # Inconnu → fallback feature
    assert ig.style_prefix("inexistant") == ig.style_prefix("feature")
    # Casse insensible
    assert ig.style_prefix("VISION") == ig.style_prefix("vision")


def test_generate_visual_no_sd_url_returns_none():
    ig = _reload_module({"SD_API_URL": ""})
    result = asyncio.run(ig.generate_visual("test prompt", "vision"))
    assert result is None


def test_generate_visual_sd_unreachable_returns_none():
    # Pointer SD_API_URL vers une adresse injoignable → fallback None
    ig = _reload_module({"SD_API_URL": "http://127.0.0.1:1",
                         "SD_TIMEOUT_SECONDS": "1.0"})
    result = asyncio.run(ig.generate_visual("test prompt", "feature"))
    assert result is None


def test_generate_visual_mock_success(monkeypatch):
    """Mock httpx pour simuler une réponse SD 200 avec base64."""
    ig = _reload_module({"SD_API_URL": "http://mock-sd.local",
                         "SD_TIMEOUT_SECONDS": "1.0"})

    class _Resp:
        status_code = 200

        def json(self):
            return {"images": ["BASE64FAKEPNG"]}

    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return _Resp()

    monkeypatch.setattr(ig.httpx, "AsyncClient", _Client)
    result = asyncio.run(ig.generate_visual("vision souveraine", "vision"))
    assert result == "BASE64FAKEPNG"


def test_generate_visual_empty_images_returns_none(monkeypatch):
    ig = _reload_module({"SD_API_URL": "http://mock-sd.local"})

    class _Resp:
        status_code = 200
        def json(self): return {"images": []}

    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return _Resp()

    monkeypatch.setattr(ig.httpx, "AsyncClient", _Client)
    result = asyncio.run(ig.generate_visual("x", "vision"))
    assert result is None
