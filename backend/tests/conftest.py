"""
Shared pytest config — must load backend/.env BEFORE any test imports
services.crypto (which reads LAURENTIA_ENCRYPTION_KEY at module import time).

Without this, the test process would use the placeholder key while the
live server (loaded via supervisor) uses the real .env key — causing
decrypt_text() to fail on records inserted by the running API.
"""
import pathlib
from dotenv import load_dotenv

# /app/backend/.env
load_dotenv(pathlib.Path(__file__).resolve().parents[1] / ".env")
