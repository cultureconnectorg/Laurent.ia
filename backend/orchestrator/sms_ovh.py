"""
sms_ovh.py — Client OVH SMS API (souverain, asynchrone, httpx).

Endpoint : POST https://eu.api.ovh.com/1.0/sms/{serviceName}/jobs
Signature SHA1 : "$1$" + sha1(AS + "+" + CK + "+" + METHOD + "+" + URL + "+" + BODY + "+" + TSTAMP)

Comportement Go-LIVE :
  - Si OVH_APPLICATION_KEY/_SECRET/_CONSUMER_KEY/_SMS_SERVICE_NAME ou FOUNDER_PHONE_NUMBER absent
    → log only, NO réseau. La fonction retourne {"sent": False, "reason": "not_configured"}.
  - Si timeout/network/4xx/5xx → {"sent": False, "reason": "..."} (jamais lève).
  - Si succès → {"sent": True, "ovh_job": {...}}.

L'alerte SMS ne doit JAMAIS bloquer le pipeline Laurent.ia. Best-effort.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OVH_API_ENDPOINT = os.environ.get("OVH_API_ENDPOINT", "https://eu.api.ovh.com/1.0").rstrip("/")
OVH_TIMEOUT = float(os.environ.get("OVH_TIMEOUT_SECONDS", "8.0"))


def _env() -> dict[str, str]:
    return {
        "app_key":   os.environ.get("OVH_APPLICATION_KEY", ""),
        "app_secret":os.environ.get("OVH_APPLICATION_SECRET", ""),
        "ck":        os.environ.get("OVH_CONSUMER_KEY", ""),
        "service":   os.environ.get("OVH_SMS_SERVICE_NAME", ""),
        "to":        os.environ.get("FOUNDER_PHONE_NUMBER", ""),
        "sender":    os.environ.get("OVH_SMS_SENDER", ""),  # optionnel — sinon OVH choisit
    }


def _configured() -> bool:
    e = _env()
    return all([e["app_key"], e["app_secret"], e["ck"], e["service"], e["to"]])


def _build_signature(app_secret: str, ck: str, method: str, url: str, body: str, ts: int) -> str:
    to_sign = "+".join([app_secret, ck, method.upper(), url, body, str(ts)])
    return "$1$" + hashlib.sha1(to_sign.encode("utf-8")).hexdigest()


async def _get_server_time(client: httpx.AsyncClient) -> int:
    r = await client.get(f"{OVH_API_ENDPOINT}/auth/time")
    r.raise_for_status()
    return int(r.text.strip())


def format_alert_body(*, agent: str, incident_id: str, summary: str) -> str:
    """Format SMS standard Laurent.ia."""
    body = f"[ALERTE LAURENTIA] Agent: {agent} | Incident: {incident_id} | Action: Valider/Bloquer/Modifier"
    if summary:
        body += f" | {summary[:60]}"
    return body[:160]


async def send_alert_sms(*, agent: str, incident_id: str, summary: str = "") -> dict[str, Any]:
    """
    Envoie un SMS d'alerte au Founder.

    Best-effort : ne lève jamais, retourne un dict de diagnostic.
    """
    if not _configured():
        logger.info("sms_ovh: not configured, skip SMS (incident=%s)", incident_id)
        return {"sent": False, "reason": "not_configured", "incident_id": incident_id}

    e = _env()
    message = format_alert_body(agent=agent, incident_id=incident_id, summary=summary)
    path = f"/sms/{e['service']}/jobs"
    url = f"{OVH_API_ENDPOINT}{path}"
    payload: dict[str, Any] = {
        "message": message,
        "receivers": [e["to"]],
        "noStopClause": True,
    }
    if e["sender"]:
        payload["sender"] = e["sender"]
    body_str = json.dumps(payload, separators=(",", ":"))

    try:
        async with httpx.AsyncClient(timeout=OVH_TIMEOUT) as client:
            ts = await _get_server_time(client)
            sig = _build_signature(e["app_secret"], e["ck"], "POST", url, body_str, ts)
            headers = {
                "X-Ovh-Application": e["app_key"],
                "X-Ovh-Timestamp": str(ts),
                "X-Ovh-Signature": sig,
                "X-Ovh-Consumer": e["ck"],
                "Content-Type": "application/json",
            }
            r = await client.post(url, headers=headers, content=body_str)
        if r.status_code in (200, 201):
            logger.info("sms_ovh: SMS sent incident=%s", incident_id)
            return {"sent": True, "ovh_job": r.json(), "incident_id": incident_id}
        logger.warning("sms_ovh: non-2xx status=%s body=%s", r.status_code, r.text[:200])
        return {"sent": False, "reason": f"status_{r.status_code}", "incident_id": incident_id}
    except Exception as ex:
        logger.warning("sms_ovh: send failed (best-effort): %s", ex)
        return {"sent": False, "reason": f"exception:{ex.__class__.__name__}", "incident_id": incident_id}
