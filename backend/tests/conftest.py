"""
Shared pytest config — must load backend/.env BEFORE any test imports
services.crypto (which reads LAURENTIA_ENCRYPTION_KEY at module import time).

Without this, the test process would use the placeholder key while the
live server (loaded via supervisor) uses the real .env key — causing
decrypt_text() to fail on records inserted by the running API.
"""
import os
import pathlib

import pytest
from dotenv import load_dotenv

from _harness import network_guard  # tests/ is on sys.path (rootdir conftest)

# /app/backend/.env
load_dotenv(pathlib.Path(__file__).resolve().parents[1] / ".env")

# Tests run outside production unless a test says otherwise (S1.4 startup checks).
os.environ.setdefault("APP_ENV", "test")

# S1.3 — no test may reach a host outside loopback.
network_guard.install()


@pytest.fixture(autouse=True)
def _no_egress():
    """Fail the test that attempted an outbound connection, even if the code swallowed the error."""
    before = len(network_guard.ATTEMPTS)
    yield
    attempts = network_guard.ATTEMPTS[before:]
    if attempts:
        details = "; ".join(f"{a['kind']} {a['target']} from {a['origin']}" for a in attempts)
        pytest.fail(f"network egress attempted: {details}", pytrace=False)


@pytest.fixture(scope="session")
def app_client():
    """One in-process client (one event loop) for the whole session: the application's
    Motor client binds to the first loop that uses it."""
    from fastapi.testclient import TestClient
    from server import app

    with TestClient(app) as client:
        yield client
