"""
Laurent.ia — backend principal (FastAPI).
ADDITIF — préserve les routes /api/status héritées du template.
"""
from fastapi import FastAPI, APIRouter
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
    return {
        "ok": True,
        "service": "laurentia",
        "model": os.environ.get("LAURENTIA_CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
    }


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
from routes.brain import router as brain_router  # noqa: E402
from routes.omega import router as omega_router  # noqa: E402
from routes.auth import router as auth_router  # noqa: E402
from routes.billing import router as billing_router, webhook_router as billing_webhook  # noqa: E402
from routes.pdf_export import router as pdf_export_router  # noqa: E402
from routes.echo import (  # noqa: E402
    private_router as echo_private_router,
    public_router as echo_public_router,
)
from routes.rgpd_purge import router as rgpd_purge_router, schedule_periodic_purge  # noqa: E402

app.include_router(laurentia_router)
app.include_router(laurentia_sessions_router)
app.include_router(brain_router)
app.include_router(omega_router)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(billing_webhook)
app.include_router(pdf_export_router)
app.include_router(echo_private_router)
app.include_router(echo_public_router)
app.include_router(rgpd_purge_router)


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
    logger.info("Laurent.ia startup complete — model=%s", os.environ.get("LAURENTIA_CLAUDE_MODEL"))


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
