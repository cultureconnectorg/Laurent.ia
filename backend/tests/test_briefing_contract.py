from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from server import app

client = TestClient(app)


def test_briefing_contract():
    with patch("routes.brain.cvl_brain.chat_enriched", new=AsyncMock(return_value="Briefing OK")):
        response = client.post("/api/brain/briefing", json={
            "topic": "Kiltikonet Code",
            "context": {"surface": "cockpit"},
            "trace_id": "trc-test",
            "issuer": "meta-cvln-os",
        })
    assert response.status_code == 200
    data = response.json()
    assert data["contract"] == "laurentia.briefing"
    assert data["version"] == "1.0"
    assert data["trace_id"] == "trc-test"
    assert data["issuer"] == "meta-cvln-os"
    assert data["response"] == "Briefing OK"
