"""
cs_common.py - shared helpers for the CleanSweep Momence scripts (27 Oct 2026)

Used by:
  sync_members.py               copies Momence customers into Supabase public.momence_members
  process_momence_tag_queue.py  applies queued Karma Yogi tags (public.momence_tag_requests)

Credentials are NOT stored here. They are read from the existing Momence .env file, by default
  C:\\Users\\markj\\OneDrive - MFPL\\Documents\\Customer Projects\\Ritual\\Momence_data\\.env
(override with the MOMENCE_DATA_DIR or MOMENCE_ENV_FILE environment variables). That file already
holds MOMENCE_* (used by momence_api_client.py) and SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY
(used by momence_courses_sync.py).
"""
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
MOMENCE_SERVICES_DIR = HERE.parent  # services/momence (holds momence_api_client.py)
DEFAULT_DATA_DIR = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data"
DATA_DIR = Path(os.environ.get("MOMENCE_DATA_DIR", DEFAULT_DATA_DIR))
ENV_FILE = Path(os.environ.get("MOMENCE_ENV_FILE", str(DATA_DIR / ".env")))
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)

if str(MOMENCE_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(MOMENCE_SERVICES_DIR))
from momence_api_client import MomenceAPIClient  # noqa: E402

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "https://rfjygyqijwgkmxboddup.supabase.co").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY") or ""
MOMENCE_API = "https://api.momence.com/api/v2"

_LOCAL_LOG_DIR = Path(r"C:\Users\markj\Momence_local_logs")
BATCH_LOG_FILE = (_LOCAL_LOG_DIR if _LOCAL_LOG_DIR.is_dir() else DATA_DIR / "Log_files") / "Momence_batch_log.txt"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    print(f"{datetime.now().strftime('%H:%M:%S')} {msg}", flush=True)


def batch_log(message: str) -> None:
    """Append one line to the shared Momence batch log (same file the nightly chain uses)."""
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"
    for attempt in range(6):
        try:
            BATCH_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(BATCH_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
            return
        except Exception as exc:  # OneDrive / antivirus locks
            if attempt < 5:
                time.sleep(5)
            else:
                print(f"[batch log write failed: {exc}] {line.rstrip()}", file=sys.stderr)


def require_config() -> None:
    if not SUPABASE_KEY:
        raise SystemExit(f"SUPABASE_SERVICE_ROLE_KEY is not set. Expected it in {ENV_FILE}")


# ---- Supabase REST -------------------------------------------------------------------------
def _sb_headers(prefer: str | None = None) -> dict:
    # New-format secret keys (sb_secret_...) are not JWTs: send them only as apikey.
    h = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    if not SUPABASE_KEY.startswith("sb_"):
        h["Authorization"] = f"Bearer {SUPABASE_KEY}"
    if prefer:
        h["Prefer"] = prefer
    return h


def sb(method: str, path: str, params: dict | None = None, body=None, prefer: str | None = None):
    r = requests.request(method, f"{SUPABASE_URL}/rest/v1/{path}", headers=_sb_headers(prefer),
                         params=params, json=body, timeout=90)
    if not r.ok:
        raise RuntimeError(f"Supabase {method} {path}: HTTP {r.status_code} {r.text[:300]}")
    return r.json() if (r.text or "").strip() else None


# ---- Momence API ---------------------------------------------------------------------------
class Momence:
    """Signs in with the existing MomenceAPIClient (password flow, credentials from .env) and
    makes its own requests, because tag assignment returns no JSON body."""

    def __init__(self, pause: float = 0.65):
        self.client = MomenceAPIClient()
        self.client.authenticate()
        self.pause = pause  # keeps well under the ~100 requests a minute noted for this account

    def request(self, method: str, path: str, params: dict | None = None, body=None, retries: int = 4):
        r = None
        for attempt in range(retries):
            self.client._ensure_valid_token()
            r = requests.request(
                method, MOMENCE_API + path, params=params, json=body, timeout=60,
                headers={"Authorization": f"Bearer {self.client._access_token}", "Content-Type": "application/json"},
            )
            time.sleep(self.pause)
            if r.status_code == 401 and attempt == 0:
                try:
                    self.client.refresh_access_token()
                except Exception:
                    self.client.authenticate()
                continue
            if r.status_code == 429 or (r.status_code >= 500 and attempt < retries - 1):
                time.sleep(15 * (attempt + 1))
                continue
            return r
        return r

    def get_all_tags(self) -> list[dict]:
        tags, page = [], 0
        while True:
            r = self.request("GET", "/host/tags", params={"page": page, "pageSize": 100})
            if not r.ok:
                raise RuntimeError(f"Momence GET /host/tags: HTTP {r.status_code} {r.text[:200]}")
            d = r.json() or {}
            rows = d.get("payload") or []
            tags.extend(rows)
            total = (d.get("pagination") or {}).get("totalCount")
            page += 1
            if not rows or len(rows) < 100 or (total is not None and len(tags) >= total):
                return tags

    def find_member_id_by_email(self, email: str) -> int | None:
        """Search Momence customers for an exact (case-insensitive) email match."""
        email = email.strip().lower()
        r = self.request("POST", "/host/members/list", body={"page": 0, "pageSize": 20, "query": email})
        if not r.ok:
            raise RuntimeError(f"Momence member search: HTTP {r.status_code} {r.text[:200]}")
        for m in (r.json() or {}).get("payload") or []:
            if str(m.get("email") or "").strip().lower() == email and isinstance(m.get("id"), int):
                return m["id"]
        return None
