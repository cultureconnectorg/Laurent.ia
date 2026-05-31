"""
test_corpus_pipeline.py — Chantier 7 corpus_pipeline.py

Couvre :
  - scoring interaction (culturel, pertinence, souverain, global)
  - format_jsonl + scrubbing PII
  - run_corpus_pipeline avec collection vide → rapport propre
  - run_corpus_pipeline avec interactions mixées → retenues/rejetées corrects
"""
import json
import os
import asyncio
from uuid import uuid4

import pytest
import pymongo

from jobs import corpus_pipeline as cp


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _fresh_db():
    """Crée une DB de test isolée par run pour ne pas polluer."""
    cli = pymongo.MongoClient(MONGO_URL)
    name = f"{DB_NAME}_test_corpus_{uuid4().hex[:8]}"
    return cli, cli[name], name


def test_score_interaction_high_caribbean_creole():
    inter = {
        "input": "Sa ka fèt ? Ou ka palé kreyòl, lakay, lanmou, fanmi, lavi.",
        "output": "Wi, an ka palé kreyòl. Martinique, Caraïbes, souveraineté, "
                  "kiltikonet, Laurent.ia, FREK, Glissant, Césaire, Fanon. "
                  + "Réponse souveraine détaillée. " * 30,
        "user_rating": 1,
    }
    s = cp.score_interaction(inter)
    assert s["culturel"] > 0.5
    assert s["souverain"] > 0.5
    assert s["pertinence"] > 0.5
    assert s["global"] > 0.5


def test_score_interaction_low_neutral():
    inter = {"input": "Hello", "output": "Hi.", "user_rating": 0}
    s = cp.score_interaction(inter)
    assert s["global"] < 0.5


def test_format_jsonl_scrubs_pii():
    inter = {
        "input": "Mon email est test@example.com et FREK-ABC123",
        "output": "OK 06 12 34 56 78 noté",
        "user_rating": 1,
    }
    line = cp.format_jsonl(inter)
    obj = json.loads(line)
    assert "[REDACTED]" in obj["prompt"]
    assert "test@example.com" not in obj["prompt"]
    assert "FREK-ABC123" not in obj["prompt"]
    # Numéro téléphone scrubbed dans output
    assert "06 12 34 56 78" not in obj["completion"]


def test_run_corpus_pipeline_empty_collection_returns_clean_report():
    cli, db, name = _fresh_db()
    try:
        # Synchronous wrapper via asyncio + motor — utilise pymongo via run sync
        # corpus_pipeline attend motor (AsyncIOMotorDatabase) — on utilise une instance motor jetable
        from motor.motor_asyncio import AsyncIOMotorClient
        async def _go():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            return await cp.run_corpus_pipeline(adb)
        report = asyncio.run(_go())
        assert report["interactions_traitees"] == 0
        assert report["retenues"] == 0
        assert report["rejetees"] == 0
        assert report["version"] == 1
        assert report["storage_uri"] is None  # rien à uploader
    finally:
        cli.drop_database(name)


def test_run_corpus_pipeline_with_mixed_interactions():
    cli, db, name = _fresh_db()
    try:
        # Insère des interactions : 1 haute qualité, 1 basse, 1 user_rating=-1 (exclue)
        high = {
            "interaction_id": "i-high",
            "corpus_eligible": True,
            "anonymized_at": None,
            "user_rating": 1,
            "input": "Sa ka fèt, kreyòl, lakay, lanmou, fanmi, lavi, péyi",
            "output": ("Martinique Caraïbes souveraineté kiltikonet Laurent.ia "
                       "FREK Césaire. ") * 50,
        }
        low = {
            "interaction_id": "i-low",
            "corpus_eligible": True,
            "anonymized_at": None,
            "user_rating": 0,
            "input": "hi",
            "output": "ok",
        }
        excluded = {
            "interaction_id": "i-neg",
            "corpus_eligible": True,
            "anonymized_at": None,
            "user_rating": -1,
            "input": "anything",
            "output": "anything",
        }
        db.laurentia_interactions.insert_many([high, low, excluded])

        from motor.motor_asyncio import AsyncIOMotorClient
        async def _go():
            adb = AsyncIOMotorClient(MONGO_URL)[name]
            return await cp.run_corpus_pipeline(adb)
        report = asyncio.run(_go())

        # i-neg exclu en amont → seulement 2 traitées
        assert report["interactions_traitees"] == 2
        assert report["retenues"] >= 1
        assert report["rejetees"] >= 1
        # Storage local fallback créé (OVHCLOUD_S3_KEY vide en test)
        assert report["storage_uri"] is not None
        # Rapport persisté
        reports = list(db.laurentia_corpus_reports.find({}, {"_id": 0}))
        assert len(reports) == 1
        # i-high a anonymized_at fixé
        updated_high = db.laurentia_interactions.find_one({"interaction_id": "i-high"})
        assert updated_high["anonymized_at"] is not None
    finally:
        cli.drop_database(name)
