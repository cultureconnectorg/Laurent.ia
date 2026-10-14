"""
Laurent.ia — backend principal (FastAPI).
ADDITIF — préserve les routes /api/status héritées du template.
"""
import asyncio

from fastapi import FastAPI, APIRouter
from starlette.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="Laurent.ia API", version="0.1.0")
app.state.db = db


@app.get("/")
async def root_health():
    """Return a truthful service landing status; inference readiness is separate."""
    inference_configured = bool(
        os.environ.get("LAURENTIA_LOCAL_LLM_URL", "").strip()
        and os.environ.get("LAURENTIA_LOCAL_LLM_MODEL", "").strip()
    )
    return {
        "service": "laurentia",
        "status": "online",
        "inference_configured": inference_configured,
        "inference_status": "configured" if inference_configured else "not_configured",
        "health_url": "/api/health",
        "inference_readiness_url": "/api/health/inference",
    }

# Routes héritées /api/status (template)
api_router = APIRouter(prefix="/api")


class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


@api_router.get("/")
async def root():
    return {"message": "Laurent.ia online", "version": "0.1.0"}


@api_router.get("/health")
async def health():
    # This reports configuration only; it does not claim the model is reachable.
    inference_configured = bool(
        os.environ.get("LAURENTIA_LOCAL_LLM_URL", "").strip()
        and os.environ.get("LAURENTIA_LOCAL_LLM_MODEL", "").strip()
    )
    return {
        "ok": True,
        "service": "laurentia",
        "model": os.environ.get("LAURENTIA_LOCAL_LLM_MODEL", "").strip() or None,
        "inference_configured": inference_configured,
        "inference_status": "configured" if inference_configured else "not_configured",
    }


@api_router.get("/health/inference")
async def inference_health():
    """Probe the configured sovereign model catalogue without exposing secrets."""
    model = os.environ.get("LAURENTIA_LOCAL_LLM_MODEL", "").strip() or None
    if not os.environ.get("LAURENTIA_LOCAL_LLM_URL", "").strip() or not model:
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "configured": False,
                "reachable": False,
                "model": model,
                "reason": "not_configured",
            },
        )

    try:
        from urllib.parse import urlparse, urlunparse
        import httpx
        from services.cvl_brain import _local_endpoint

        endpoint, model, api_key, timeout = _local_endpoint()
        parsed = urlparse(endpoint)
        path = parsed.path.rstrip("/")
        models_path = path[:-len("chat/completions")] + "models"
        models_url = urlunparse(parsed._replace(path=models_path, query="", fragment=""))
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(min(timeout, 8.0), connect=min(timeout, 3.0)),
            follow_redirects=False,
            trust_env=False,
        ) as inference_client:
            response = await asyncio.wait_for(
                inference_client.get(models_url, headers=headers),
                timeout=8.0,
            )
            response.raise_for_status()
            payload = response.json()

        model_rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(model_rows, list):
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "configured": True,
                    "reachable": True,
                    "model": model,
                    "reason": "invalid_model_catalogue",
                },
            )
        available_models = {
            item.get("id") for item in model_rows
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        model_available = model in available_models
        return JSONResponse(
            status_code=200 if model_available else 503,
            content={
                "ok": model_available,
                "configured": True,
                "reachable": True,
                "model": model,
                "model_available": model_available,
                "reason": "ready" if model_available else "configured_model_not_listed",
            },
        )
    except Exception as exc:
        # Deliberately avoid returning exception text, URLs, or credentials.
        reason = "timeout" if isinstance(exc, asyncio.TimeoutError) else "invalid_configuration"
        try:
            import httpx
            if isinstance(exc, httpx.HTTPError):
                reason = "endpoint_unreachable"
        except ImportError:
            pass
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "configured": True,
                "reachable": False,
                "model": model,
                "reason": reason,
            },
        )


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.model_dump())
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.status_checks.insert_one(doc)
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    rows = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for r in rows:
        if isinstance(r['timestamp'], str):
            r['timestamp'] = datetime.fromisoformat(r['timestamp'])
    return rows


app.include_router(api_router)

# Routes Laurent.ia (additif)
from routes.laurentia_gateway import router as laurentia_router  # noqa: E402
from routes.laurentia_sessions import router as laurentia_sessions_router  # noqa: E402
from routes.brain import router as brain_router, briefing as brain_briefing  # noqa: E402
from routes.omega import router as omega_router  # noqa: E402
from routes.auth import router as auth_router  # noqa: E402
from routes.billing import router as billing_router, webhook_router as billing_webhook  # noqa: E402
from routes.pdf_export import router as pdf_export_router  # noqa: E402
from routes.echo import (  # noqa: E402
    private_router as echo_private_router,
    public_router as echo_public_router,
)
from routes.rgpd_purge import router as rgpd_purge_router, schedule_periodic_purge  # noqa: E402
from routes.social_admin import router as social_admin_router  # noqa: E402
from routes.orchestrator_admin import (  # noqa: E402
    router as orchestrator_admin_router,
    webhook_router as orchestrator_webhook_router,
)
from routes.reports import router as reports_router  # noqa: E402
from jobs.corpus_pipeline import schedule_corpus_pipeline  # noqa: E402
from jobs.social_agent import schedule_social_agent  # noqa: E402
from jobs.reports import schedule_reports  # noqa: E402
from orchestrator.orchestrator import make_orchestrator  # noqa: E402

app.include_router(laurentia_router)
app.include_router(laurentia_sessions_router)
app.include_router(brain_router)
# Alias de compatibilité Meta CVLN : réutilise strictement le même handler,
# le même schéma de requête et la même authentification inter-services.
app.add_api_route(
    "/api/briefing",
    brain_briefing,
    methods=["POST"],
    tags=["briefing-compat"],
)
app.include_router(omega_router)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(billing_webhook)
app.include_router(pdf_export_router)
app.include_router(echo_private_router)
app.include_router(echo_public_router)
app.include_router(rgpd_purge_router)
app.include_router(social_admin_router)
app.include_router(orchestrator_admin_router)
app.include_router(orchestrator_webhook_router)
app.include_router(reports_router)


# Exception handler — Kiltikonet panne amont → HTTP 503 (strict v1.2-LIVE).
# LabelOS reste en fallback silencieux (stub) côté service ; pas de handler ici.
from fastapi.responses import JSONResponse  # noqa: E402
from services.kiltikonet_bridge import KiltikonetUnavailable  # noqa: E402


@app.exception_handler(KiltikonetUnavailable)
async def kiltikonet_unavailable_handler(_request, exc):
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Service d'identité indisponible (Kiltikonet). Réessaie dans quelques instants.",
            "code": "kiltikonet_unavailable",
        },
    )


# CORS — supporte credentials (cookies httpOnly) avec allow_origin_regex
_cors_env = os.environ.get('CORS_ORIGINS', '*').strip()
if _cors_env == '*':
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origin_regex=".*",
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=_cors_env.split(','),
        allow_methods=["*"],
        allow_headers=["*"],
    )

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def on_startup():
    from services.cvl_brain_agents import ensure_registry
    from services.rate_limit_mongo import ensure_indexes as ensure_ratelimit_indexes
    await ensure_registry(db)
    await ensure_ratelimit_indexes(db)
    schedule_periodic_purge(app, db)
    # Chantier 7 — Autonomie & Apprentissage continu
    if os.environ.get("CHANTIER7_SCHEDULERS_DISABLED", "").lower() not in ("1", "true", "yes"):
        schedule_corpus_pipeline(app, db)
        schedule_social_agent(app, db)
    # Chantier 9 — Orchestrateur 20 agents (mode SHADOW par défaut)
    if os.environ.get("ORCHESTRATOR_DISABLED", "").lower() not in ("1", "true", "yes"):
        orch = make_orchestrator(db)
        orch.start()
        app.state.orchestrator = orch
        logger.info("Orchestrator chantier-9 ready — 20 agents WARM")
    # Chantier 10 — Reports daily/weekly (cron 00:00 Martinique)
    if os.environ.get("CHANTIER10_REPORTS_DISABLED", "").lower() not in ("1", "true", "yes"):
        schedule_reports(app, db)
    logger.info("Laurent.ia startup complete — model=%s inference_configured=%s", os.environ.get("LAURENTIA_LOCAL_LLM_MODEL", "local-model"), bool(os.environ.get("LAURENTIA_LOCAL_LLM_URL", "").strip()))


@app.on_event("shutdown")
async def shutdown_db_client():
    orch = getattr(app.state, "orchestrator", None)
    if orch is not None:
        orch.stop()
    client.close()
