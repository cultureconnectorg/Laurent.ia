"""Loaded automatically when this directory is on PYTHONPATH: puts a locally
started API (uvicorn) under the same network guard as the tests."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from _harness import network_guard  # noqa: E402

network_guard.install()
