from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from server import app

client = TestClient(app)


def test_briefing_contract():
    with patch.dict("os.environ", {"LAURENTIA_CVLN_SERVICE_API_KEY": "svc-cvln-test"}), \
         patch("routes.brain.cvl_brain.chat_enriched", new=AsyncMock(return_value="Briefing OK")):
        response = client.post("/api/brain/briefing", headers={"X-API-Key": "svc-cvln-test"}, json={
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


def test_briefing_rejects_missing_api_key():
    with patch.dict("os.environ", {"LAURENTIA_CVLN_SERVICE_API_KEY": "svc-cvln-test"}):
        response = client.post("/api/brain/briefing", json={"topic": "x"})
    assert response.status_code == 403


def test_briefing_rejects_user_style_laurentia_key():
    with patch.dict("os.environ", {"LAURENTIA_CVLN_SERVICE_API_KEY": "svc-cvln-test"}):
        response = client.post("/api/brain/briefing", headers={"X-API-Key": "lia_creator_userkey"}, json={"topic": "x"})
    assert response.status_code == 403
