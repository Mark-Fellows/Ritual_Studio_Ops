"""
config.py — Shared configuration for Cover Management (RSO edition)
====================================================================
RSO Phase 3 version. Identical public API to the CM legacy config.py,
but resolves .env from the Ritual_Studio_Ops project root rather than
from the Ritual_Cover_Management root, and imports MomenceAPIClient from
services/momence/ rather than via a hardcoded OneDrive path.

Import this module from any stage script to get a consistent config object
and ready-to-use Supabase REST helpers.

All stage scripts that previously did:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import ...
continue to work unchanged — their parent.parent now resolves to
services/cover/ where this file lives.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# ── Locate and load .env from the RSO project root ────────────────────────────
# services/cover/ -> services/ -> Ritual_Studio_Ops/ -> .env
_HERE     = Path(__file__).parent                   # services/cover/
_RSO_ROOT = _HERE.parent.parent                     # Ritual_Studio_Ops/
_env_path = _RSO_ROOT / ".env"

if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=True)
else:
    # Fallback: try sibling Momence_data .env (legacy; should not be needed in RSO)
    _alt = Path(
        r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\.env"
    )
    if _alt.exists():
        load_dotenv(dotenv_path=_alt)

# ── Add services/momence/ to sys.path so MomenceAPIClient is importable ───────
# Replaces the hardcoded _MOMENCE_DIR sys.path.insert in each stage file.
_MOMENCE_SERVICES = _HERE.parent / "momence"        # services/momence/
if _MOMENCE_SERVICES.exists() and str(_MOMENCE_SERVICES) not in sys.path:
    sys.path.insert(0, str(_MOMENCE_SERVICES))

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rfjygyqijwgkmxboddup.supabase.co")

SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJmanlneXFpandna"
    "214Ym9kZHVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3NDU5MjksImV4cCI6MjA4NzMyMTkyOX0."
    "g40IEOLPDTWnbFYybWL01wZMiE_f2_yor_DKuaSCajU"
)

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
NLP_MODEL = os.getenv("NLP_MODEL", "claude-haiku-4-5-20251001")

# ── Google Gemini ─────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ── Operational settings ──────────────────────────────────────────────────────
INITIAL_TEACHER_GRADE     = int(os.getenv("INITIAL_TEACHER_GRADE", "10"))
SYNC_LOOKBACK_DAYS        = int(os.getenv("SYNC_LOOKBACK_DAYS", "365"))
WHATSAPP_LOOKBACK_HOURS   = int(os.getenv("WHATSAPP_LOOKBACK_HOURS", "6"))
NLP_CONFIDENCE_THRESHOLD  = float(os.getenv("NLP_CONFIDENCE_THRESHOLD", "0.70"))

# ── Browser settings ──────────────────────────────────────────────────────────
CHROME_DEBUG_PORT = int(os.getenv("CHROME_DEBUG_PORT", "9222"))
CHROME_PATH = os.getenv(
    "CHROME_PATH",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)

# ── SMTP (stage 4 notifier) ───────────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFY_FROM   = os.getenv("NOTIFY_FROM", f"Ritual Studios <{SMTP_USER}>")
NOTIFY_REPLY_TO = os.getenv("NOTIFY_REPLY_TO", SMTP_USER)

# ── Momence data directory (master CSVs) ──────────────────────────────────────
MOMENCE_DATA_DIR = Path(
    os.getenv(
        "MOMENCE_DATA_DIR",
        r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data",
    )
)

# ── Disciplines reference (Phase 1 canonical codes) ───────────────────────────
# These map Momence/WhatsApp text patterns to the Phase 1 disciplines.code values.
# Previously duplicated in CM discipline_mappings table and DISCIPLINE_PATTERNS.
DISCIPLINE_CODES = {
    "yoga":        "yoga",
    "yin":         "yin",
    "mat_pilates": "mat_pilates",
    "barre":       "barre",
    "reformer":    "reformer",
}

# ── Supabase REST helpers ─────────────────────────────────────────────────────
import requests  # noqa: E402 (after env load)

def _headers(service_key: bool = False) -> dict:
    key = (os.getenv("SUPABASE_SERVICE_KEY") or SUPABASE_KEY) if service_key else SUPABASE_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def sb_get(path: str, *, service_key: bool = False, timeout: int = 30) -> list:
    """GET from Supabase REST. Returns list (may be empty)."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    r = requests.get(url, headers=_headers(service_key), timeout=timeout)
    r.raise_for_status()
    return r.json()


def sb_post(path: str, payload: dict, *, service_key: bool = True, timeout: int = 30) -> dict:
    """POST to Supabase REST. Returns inserted row."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    r = requests.post(url, headers=_headers(service_key), json=payload, timeout=timeout)
    r.raise_for_status()
    result = r.json()
    return result[0] if isinstance(result, list) and result else result


def sb_patch(path: str, payload: dict, *, service_key: bool = True, timeout: int = 30) -> list:
    """PATCH (update) rows in Supabase REST. Returns updated rows."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    r = requests.patch(url, headers=_headers(service_key), json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def get_config_value(key: str, default: str = "") -> str:
    """Read a value from the system_config table. Falls back to default."""
    try:
        rows = sb_get(f"system_config?key=eq.{key}&select=value&limit=1")
        if rows:
            return rows[0].get("value", default)
    except Exception:
        pass
    return default
