"""
momence_teacher_sync.py -- Stage 1
Syncs teacher records from Momence session history into the Supabase
teachers table.  Only writes fields that are currently empty (never
downgrades existing grades or removes existing data).

Usage
-----
    python momence_teacher_sync.py              # live run
    python momence_teacher_sync.py --dry-run   # preview changes only
    python momence_teacher_sync.py --days 180  # shorter lookback window
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import requests

# ── RSO Phase 3: config.py resolves .env and sets services/momence/ on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (  # noqa: E402
    SUPABASE_URL, SUPABASE_KEY, INITIAL_TEACHER_GRADE, SYNC_LOOKBACK_DAYS,
    DISCIPLINE_CODES, sb_get, sb_post, sb_patch,
)
from momence_api_client import MomenceAPIClient  # noqa: E402 (path set by config)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rfjygyqijwgkmxboddup.supabase.co")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJmanlneXFpandna"
    "214Ym9kZHVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3NDU5MjksImV4cCI6MjA4NzMyMTkyOX0."
    "g40IEOLPDTWnbFYybWL01wZMiE_f2_yor_DKuaSCajU"
)

INITIAL_GRADE = int(os.getenv("INITIAL_TEACHER_GRADE", "10"))
LOOKBACK_DAYS = int(os.getenv("SYNC_LOOKBACK_DAYS", "365"))

DISCIPLINE_PATTERNS = [
    ("reformer", "reformer"),
    ("mat pilates", "mat_pilates"),
    ("mat_pilates", "mat_pilates"),
    ("yin", "yin"),
    ("barre", "barre"),
    ("yoga", "yoga"),
]

STUDIO_MAP = {
    "robina": "Robina",
    "palm beach": "Palm Beach",
}


# ─────────────────────────────────────────────────────────────────────────────
# Supabase REST helpers
# ─────────────────────────────────────────────────────────────────────────────


def _sb_headers(prefer: str | None = None) -> dict:
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def sb_get(table: str, params: dict = None) -> list:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=_sb_headers(),
        params=params,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def sb_patch(table: str, payload: dict, match_params: dict) -> list:
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=_sb_headers(prefer="return=representation"),
        params=match_params,
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────


def normalise(s: str) -> str:
    return (s or "").strip().lower()


def infer_discipline(class_name: str) -> str | None:
    name_lower = normalise(class_name)
    for pattern, code in DISCIPLINE_PATTERNS:
        if pattern in name_lower:
            return code
    return None


def infer_studio(location_str: str) -> str | None:
    loc_lower = normalise(location_str)
    for key, val in STUDIO_MAP.items():
        if key in loc_lower:
            return val
    return None


def get_teacher_field(session_obj: dict, *field_names) -> str | None:
    teacher = (
        session_obj.get("teacher")
        or session_obj.get("instructor")
        or session_obj.get("host")
        or session_obj.get("staff")
        or {}
    )
    if not isinstance(teacher, dict):
        return None
    for name in field_names:
        val = teacher.get(name)
        if val:
            return str(val).strip()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────


def load_teachers() -> tuple[list, dict, dict]:
    print("Loading teachers from Supabase...")
    rows = sb_get(
        "teachers",
        params={
            "select": "id,first_name,last_name,email,phone,momence_ref,grades,locations,whatsapp_phone",
            "order": "last_name",
        },
    )
    by_ref = {r["momence_ref"]: r for r in rows if r.get("momence_ref")}
    by_name = {normalise(f"{r['first_name']} {r['last_name']}"): r for r in rows}
    print(f"  -> {len(rows)} teachers loaded ({len(by_ref)} with momence_ref)")
    return rows, by_ref, by_name


def fetch_sessions(client: MomenceAPIClient, lookback_days: int) -> list:
    end = datetime.now()
    start = end - timedelta(days=lookback_days)
    print(f"Fetching Momence sessions from {start:%Y-%m-%d} to {end:%Y-%m-%d}...")
    all_sessions, page = [], 0
    while True:
        batch = client.get_sessions(
            start_date=start, end_date=end, page=page, page_size=100
        )
        if not batch:
            break
        # Momence API returns {'payload': [...], 'pagination': {...}}
        pagination = {}
        if isinstance(batch, dict):
            pagination = batch.get("pagination") or {}
            batch = batch.get("payload") or []
        if not batch:
            break
        all_sessions.extend(batch)
        total = pagination.get("totalCount", "?")
        print(
            f"  page {page}: {len(batch)} sessions (fetched: {len(all_sessions)}, total: {total})"
        )
        if len(all_sessions) >= (pagination.get("totalCount") or 0):
            break
        if len(batch) < 100:
            break
        page += 1
    print(f"  -> {len(all_sessions)} sessions fetched")
    return all_sessions


# ─────────────────────────────────────────────────────────────────────────────
# Activity aggregation
# ─────────────────────────────────────────────────────────────────────────────


def build_activity_map(sessions: list) -> dict:
    activity: dict = {}
    null_teacher_count = 0
    for s in sessions:
        if not isinstance(s, dict):
            continue
        # Skip sessions with no teacher assignment (common for older Momence data)
        teacher_obj = s.get("teacher") or {}
        if not isinstance(teacher_obj, dict) or not teacher_obj:
            null_teacher_count += 1
            continue
        first = teacher_obj.get("firstName") or teacher_obj.get("first_name") or ""
        last = teacher_obj.get("lastName") or teacher_obj.get("last_name") or ""
        full = f"{first} {last}".strip()
        if not full:
            null_teacher_count += 1
            continue
        key = normalise(full)
        if key not in activity:
            activity[key] = {
                "full_name": full,
                "disciplines": set(),
                "studios": set(),
                "email": teacher_obj.get("email") or None,
                "phone": teacher_obj.get("phoneNumber")
                or teacher_obj.get("phone")
                or None,
                "momence_id": teacher_obj.get("id") or None,
            }
        # Class name field is 'name' in Momence API (not 'title')
        disc = infer_discipline(s.get("name") or "")
        if disc:
            activity[key]["disciplines"].add(disc)
        # Location is under 'inPersonLocation' (not 'location')
        loc_obj = s.get("inPersonLocation") or s.get("location") or {}
        loc_str = (
            loc_obj.get("name") if isinstance(loc_obj, dict) else str(loc_obj or "")
        )
        studio = infer_studio(loc_str or "")
        if studio:
            activity[key]["studios"].add(studio)
    if null_teacher_count:
        print(
            f"  (skipped {null_teacher_count} sessions with null teacher — normal for older Momence data)"
        )
    print(f"  -> {len(activity)} unique teachers found in session data")
    return activity


# ─────────────────────────────────────────────────────────────────────────────
# Sync logic
# ─────────────────────────────────────────────────────────────────────────────


def compute_updates(teacher: dict, activity: dict) -> dict:
    updates: dict = {}
    if not teacher.get("whatsapp_phone") and activity.get("phone"):
        updates["whatsapp_phone"] = activity["phone"]
    if not teacher.get("email") and activity.get("email"):
        updates["email"] = activity["email"]
    if not teacher.get("momence_ref") and activity.get("momence_id"):
        updates["momence_ref"] = str(activity["momence_id"])
    grades = dict(
        teacher.get("grades")
        or {"yin": 0, "yoga": 0, "barre": 0, "reformer": 0, "mat_pilates": 0}
    )
    grades_changed = False
    for disc in activity.get("disciplines", set()):
        if disc in grades and grades[disc] == 0:
            grades[disc] = INITIAL_GRADE
            grades_changed = True
    if grades_changed:
        updates["grades"] = grades
    locations = list(teacher.get("locations") or [])
    for studio in activity.get("studios", set()):
        if studio not in locations:
            locations.append(studio)
    if locations != list(teacher.get("locations") or []):
        updates["locations"] = locations
    return updates


def run(lookback_days: int = LOOKBACK_DAYS, dry_run: bool = False, insert_new: bool = False) -> None:
    mode = "[DRY RUN] " if dry_run else ""
    print(f'\n{"="*60}')
    print(f"{mode}Momence -> Teachers Sync")
    print(f"Lookback: {lookback_days} days | Initial grade: {INITIAL_GRADE}")
    print(f'{"="*60}\n')
    _, by_ref, by_name = load_teachers()
    print("\nConnecting to Momence API...")
    client = MomenceAPIClient()
    client.authenticate()
    sessions = fetch_sessions(client, lookback_days)
    print("\nBuilding activity map...")
    activity_map = build_activity_map(sessions)
    print("\nMatching and syncing...")
    print("-" * 60)
    matched = updated = unmatched = skipped = 0
    for name_key, act in activity_map.items():
        teacher = None
        if act.get("momence_id"):
            teacher = by_ref.get(str(act["momence_id"]))
        if not teacher:
            teacher = by_name.get(name_key)
        if not teacher:
            if insert_new:
                # Build a minimal teacher record from Momence activity data.
                # Grades and availability are left empty; the admin completes them.
                parts = act["full_name"].split(maxsplit=1)
                first = parts[0]
                last  = parts[1] if len(parts) > 1 else ""
                new_row = {
                    "first_name":    first,
                    "last_name":     last,
                    "home_location": "Palm Beach",
                    "locations":     ["Palm Beach"],
                    "grades":        {k: 0 for k in DISCIPLINE_CODES},
                    "avail_slots":   {},
                    "notes":         f"Auto-created by momence_teacher_sync --insert-new "
                                     f"(Momence ID: {act.get('momence_id', 'unknown')})",
                }
                if dry_run:
                    print(f'  +  WOULD INSERT: {act["full_name"]} (new teacher)')
                else:
                    result = sb_post("teachers?", new_row)
                    teacher_id = result.get("id") if isinstance(result, dict) else None
                    print(f'  +  INSERTED: {act["full_name"]} (id={teacher_id})')
                unmatched += 1
            else:
                print(f'  !  UNMATCHED: {act["full_name"]}')
                unmatched += 1
            continue
        matched += 1
        updates = compute_updates(teacher, act)
        if not updates:
            print(f'  -  {act["full_name"]}: no changes needed')
            skipped += 1
            continue
        field_list = ", ".join(updates.keys())
        if dry_run:
            print(f'  >  {act["full_name"]}: would update [{field_list}]')
            if "grades" in updates:
                print(f'       grades -> {json.dumps(updates["grades"])}')
        else:
            sb_patch("teachers", updates, match_params={"id": f'eq.{teacher["id"]}'})
            print(f'  ok {act["full_name"]}: updated [{field_list}]')
        updated += 1
    print("-" * 60)
    print(f'\nSync {"preview" if dry_run else "complete"}:')
    print(f"  Matched:   {matched}")
    print(f"  Updated:   {updated}")
    print(f"  Skipped:   {skipped}")
    print(f"  Unmatched: {unmatched}")
    if unmatched > 0:
        print("\n  Tip: Add unmatched teachers to the Teacher Management app first.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync Momence sessions -> Supabase teachers"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes only — no writes to Supabase")
    parser.add_argument("--days", type=int, default=LOOKBACK_DAYS,
                        help="Lookback window in days (default: SYNC_LOOKBACK_DAYS env var)")
    parser.add_argument("--insert-new", action="store_true",
                        help="Create new teacher rows for Momence instructors not in Supabase")
    args = parser.parse_args()
    run(lookback_days=args.days, dry_run=args.dry_run, insert_new=args.insert_new)
