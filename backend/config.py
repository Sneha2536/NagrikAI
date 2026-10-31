"""
config.py: all settings in ONE place.

Values come from the .env file in the project root (copy .env.example to .env).
Every other file does:  from config import settings
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


class Settings:
    # Bump when you change code. The frontend compares this to detect a backend that was not restarted.
    BUILD = "2026-10-31-f"

    # ---- Which AI service to use: "gemini" (has a free tier) or "anthropic" (Claude)
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    # Optional second model to try if the first is overloaded (503) or too slow.
    GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

    # ---- Real data sources
    PIB_RSS_URL = os.getenv(
        "PIB_RSS_URL", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"
    )
    MYSCHEME_API_KEY = os.getenv("MYSCHEME_API_KEY", "")
    # Optional extra CA certificates for official-document HTTPS downloads (PEM bundle).
    PDF_CA_BUNDLE = os.getenv("PDF_CA_BUNDLE", "").strip()
    MAX_DOCUMENT_BYTES = int(os.getenv("MAX_DOCUMENT_BYTES", str(25 * 1024 * 1024)))

    # ---- Limits
    # How many characters of a document we send to the AI in one go.
    MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "120000"))

    # ---- Server
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    # ---- Folders (created automatically)
    DATA_DIR = ROOT / "data"
    PDF_DIR = DATA_DIR / "pdfs"
    INDEX_DIR = DATA_DIR / "index"


settings = Settings()

for _d in (
    settings.PDF_DIR,
    settings.INDEX_DIR,
    settings.INDEX_DIR / "docs",
    settings.INDEX_DIR / "explanations",
    settings.INDEX_DIR / "rules",
):
    _d.mkdir(parents=True, exist_ok=True)
