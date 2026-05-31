"""
image_generator.py — Génération visuelle via Stable Diffusion souverain (OVHcloud).

Endpoint amont attendu : Stable Diffusion WebUI compatible
  POST {SD_API_URL}/sdapi/v1/txt2img
  Body :
    { prompt, negative_prompt, width, height, steps, cfg_scale }
  Réponse :
    { "images": ["<base64>...", ...] }

Comportement :
  - Si SD_API_URL absent → retourne None (Social Agent publiera sans visuel)
  - Si SD timeout / 5xx / network → retourne None (jamais bloquer publication)
  - Sinon → base64 image PNG
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SD_API_URL = os.environ.get("SD_API_URL", "").rstrip("/")
SD_TIMEOUT = float(os.environ.get("SD_TIMEOUT_SECONDS", "60.0"))

_STYLE_PREFIXES = {
    "vision":    "dark background, blue energy waves, Caribbean mystical",
    "culture":   "Martinique landscape, warm colors, tropical",
    "feature":   "dark tech, blue neon, sovereign AI aesthetic",
    "artiste":   "music studio, Caribbean urban, cinematic",
    "creole":    "Caribbean heritage, warm earth tones, ancestral",
    "citation":  "minimalist dark, white typography, elegant",
    "actualite": "bold graphic, Laurent.ia blue, clean modern",
}


def style_prefix(theme: str) -> str:
    """Retourne le préfixe stylistique pour un thème éditorial."""
    return _STYLE_PREFIXES.get((theme or "").lower(), _STYLE_PREFIXES["feature"])


def _bridge_configured() -> bool:
    return bool(SD_API_URL)


async def generate_visual(prompt: str, theme: str) -> Optional[str]:
    """
    Génère un visuel 1080x1080 via Stable Diffusion.

    Retourne :
      - str base64 PNG si succès
      - None si SD non configuré OU si la génération échoue (fallback silencieux)
    """
    if not _bridge_configured():
        logger.info("image_generator: SD_API_URL non défini, fallback None")
        return None

    full_prompt = f"{prompt}, {style_prefix(theme)}"
    payload = {
        "prompt": full_prompt,
        "negative_prompt": "blurry, watermark, low quality, text",
        "width": 1080,
        "height": 1080,
        "steps": 20,
        "cfg_scale": 7,
    }

    try:
        async with httpx.AsyncClient(timeout=SD_TIMEOUT) as client:
            r = await client.post(f"{SD_API_URL}/sdapi/v1/txt2img", json=payload)
        if r.status_code != 200:
            logger.warning("image_generator: SD non-200 status=%s", r.status_code)
            return None
        data = r.json()
        images = data.get("images") or []
        if not images:
            logger.warning("image_generator: SD réponse sans images")
            return None
        return images[0]
    except Exception as e:
        logger.warning("image_generator: SD failed (fallback None): %s", e)
        return None
