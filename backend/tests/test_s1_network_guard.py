"""S1.3 — the network guard really refuses egress and reports it."""
import socket

import pytest
import requests

from _harness import network_guard


@pytest.fixture
def isolated_attempts():
    before = len(network_guard.ATTEMPTS)
    yield
    # Attempts made on purpose here must not fail this test through the autouse check.
    del network_guard.ATTEMPTS[before:]


def test_external_dns_is_refused_and_recorded(isolated_attempts):
    before = len(network_guard.ATTEMPTS)
    with pytest.raises(socket.gaierror):
        socket.getaddrinfo("example.org", 443)
    assert network_guard.ATTEMPTS[before]["kind"] == "dns"
    assert network_guard.ATTEMPTS[before]["target"] == "example.org"


def test_external_ip_connect_is_refused_and_recorded(isolated_attempts):
    before = len(network_guard.ATTEMPTS)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(ConnectionRefusedError):
            s.connect(("93.184.216.34", 443))
    finally:
        s.close()
    assert network_guard.ATTEMPTS[before]["target"] == "93.184.216.34:443"


def test_swallowed_http_error_is_still_recorded(isolated_attempts):
    """Code that catches the error (as the bridges do) cannot hide the attempt."""
    before = len(network_guard.ATTEMPTS)
    try:
        requests.get("https://api.example.org/v1", timeout=2)
    except requests.RequestException:
        pass
    assert any(a["target"] == "api.example.org" for a in network_guard.ATTEMPTS[before:])


def test_loopback_is_allowed():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        c.connect(s.getsockname())
    finally:
        c.close()
        s.close()
