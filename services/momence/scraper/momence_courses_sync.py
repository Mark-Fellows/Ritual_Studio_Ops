"""
momence_courses_sync.py
=======================
Syncs training course data from Momence into Supabase (training_courses and
trainee_enrollments tables) and writes audit CSV files.

HOW IT WORKS
------------
1. Reads the latest momence_classes_f_*.csv (generated nightly by the existing
   sessions pipeline — no extra API calls needed for session discovery).
2. Identifies course sessions by matching Class Name against COURSE_KEYWORDS.
3. Groups sessions by normalised course name (multiple dates = one course).
4. For each course group, calls get_session_bookings() for each session ID
   and deduplicates trainees by Momence member ID.
5. Matches each course to an existing training_courses record in Supabase
   (by normalised name). Creates a new record if no match is found.
6. For each unique trainee:
   - Looks up or creates a teachers record (matched by email).
   - Creates or skips a trainee_enrollments record.
7. Writes master_courses.csv and master_course_trainees.csv as audit trail.
8. Logs to Log_files/momence_courses_sync_YYYY_MM_DD_HH_MM.txt.

ADDING NEW COURSE TYPES
-----------------------
Edit COURSE_KEYWORDS below. Any session whose Class Name contains one of
these strings (case-insensitive) will be treated as a training course.

REQUIREMENTS
------------
pip install requests python-dotenv  (already installed for existing pipeline)
.env must contain SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
"""

import csv
import glob
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

# ── Resolve paths relative to this script ────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from momence_api_client import MomenceAPIClient

load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

# ── Configuration ─────────────────────────────────────────────────────────────

# Session names containing any of these strings (case-insensitive) are treated
# as training courses. Edit this list to add new course types.
COURSE_KEYWORDS = [
    "teacher training",
    "yoga training",
    "pilates training",
    "reformer training",
    "barre training",
    "yin training",
    "mat training",
    "200hr",
    "300hr",
    "training program",
    "certification",
    "certif",
]

# Map fragments of a course name to a discipline value stored in Supabase.
DISCIPLINE_MAP = {
    "yoga": "yoga",
    "yin": "yin",
    "pilates": "mat_pilates",
    "reformer": "reformer",
    "barre": "barre",
    "mat": "mat_pilates",
}

# Default grades JSON for a new trainee teacher record.
DEFAULT_GRADES = {"yoga": 0, "yin": 0, "barre": 0, "reformer": 0, "mat_pilates": 0}

# File paths
CLASSES_GLOB    = str(SCRIPT_DIR / "momence_classes_f_*.csv")
MASTER_COURSES  = str(SCRIPT_DIR / "master_courses.csv")
MASTER_TRAINEES = str(SCRIPT_DIR / "master_course_trainees.csv")
LOG_DIR         = SCRIPT_DIR / "Log_files"
# Master batch log — moved out of OneDrive on 2026-05-18 to stop sync locks
# truncating writes. Falls back to the legacy in-tree path if the local
# folder is absent (e.g. clean checkout on a new machine).
from pathlib import Path as _Path
_LOCAL_BATCH_LOG_DIR = _Path(r"C:\Users\markj\Momence_local_logs")
if _LOCAL_BATCH_LOG_DIR.is_dir():
    BATCH_LOG_FILE = _LOCAL_BATCH_LOG_DIR / "Momence_batch_log.txt"
else:
    BATCH_LOG_FILE = LOG_DIR / "Momence_batch_log.txt"

# Supabase
SUPABASE_URL     = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# API page size for session bookings
BOOKINGS_PAGE_SIZE = 100


# ── Logging ───────────────────────────────────────────────────────────────────

def setup_logging(ts: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(LOG_DIR / f"momence_courses_sync_{ts}.txt"),
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )


def batch_log(message: str) -> None:
    BATCH_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} - {message}\n"
    for attempt in range(6):
        try:
            with open(BATCH_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
            return
        except Exception as exc:
            if attempt < 5:
                time.sleep(5)
            else:
                print(f"[BATCH LOG WRITE FAILED after 6 attempts: {exc}] {line.rstrip()}", file=sys.stderr)


def log(msg: str) -> None:
    print(msg)
    logging.info(msg)


# ── Supabase helpers ──────────────────────────────────────────────────────────

def _sb_headers(upsert: bool = False) -> Dict[str, str]:
    prefer = "resolution=merge-duplicates,return=representation" if upsert else "return=representation"
    return {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def sb_get(table: str, params: Dict[str, str] = None) -> List[Dict]:
    """Fetch all rows from a Supabase table (no pagination — assumes small datasets)."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    resp = requests.get(url, headers=_sb_headers(), params=params or {})
    resp.raise_for_status()
    return resp.json()


def sb_post(table: str, data: Dict) -> Dict:
    """Insert a single row and return the created record."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    resp = requests.post(url, headers=_sb_headers(), json=data)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if isinstance(rows, list) and rows else {}


def sb_upsert(table: str, data: Dict, on_conflict: str) -> Dict:
    """Upsert a row (insert or update on conflict column)."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    resp = requests.post(url, headers=_sb_headers(upsert=True), json=data)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if isinstance(rows, list) and rows else {}


def sb_patch(table: str, match_col: str, match_val: str, data: Dict) -> None:
    """Update rows matching match_col=match_val."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{match_val}"
    resp = requests.patch(url, headers=_sb_headers(), json=data)
    resp.raise_for_status()


# ── Course identification ─────────────────────────────────────────────────────

def normalise_name(name: str) -> str:
    """Lowercase, strip extra whitespace — used for matching."""
    return re.sub(r"\s+", " ", name.strip().lower())


def is_course(class_name: str) -> bool:
    n = class_name.lower()
    return any(kw in n for kw in COURSE_KEYWORDS)


def derive_discipline(course_name: str) -> str:
    n = course_name.lower()
    for fragment, discipline in DISCIPLINE_MAP.items():
        if fragment in n:
            return discipline
    return "yoga"  # fallback


def read_latest_classes_csv() -> List[Dict]:
    """Return rows from the most-recently-modified momence_classes_f_*.csv."""
    files = sorted(glob.glob(CLASSES_GLOB), key=os.path.getmtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No files matching {CLASSES_GLOB}")
    latest = files[0]
    log(f"Reading classes from: {Path(latest).name}")
    with open(latest, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def group_courses(rows: List[Dict]) -> Dict[str, Dict]:
    """
    Return a dict keyed by normalised course name.
    Each value: {display_name, discipline, location, session_ids, dates}
    """
    groups: Dict[str, Dict] = {}
    for row in rows:
        name = row.get("Class Name", "").strip()
        if not is_course(name):
            continue
        key = normalise_name(name)
        session_id = row.get("Class Number", "").strip()
        date_str   = row.get("Date", "").strip()       # e.g. "06 Apr 2026"
        location   = row.get("Location", "").strip()

        if key not in groups:
            groups[key] = {
                "display_name": name,
                "discipline":   derive_discipline(name),
                "location":     location,
                "session_ids":  [],
                "dates":        [],
            }
        if session_id:
            groups[key]["session_ids"].append(session_id)
        if date_str:
            groups[key]["dates"].append(date_str)

    # Sort session dates and derive commence/completion dates
    for key, g in groups.items():
        parsed = []
        for d in g["dates"]:
            try:
                parsed.append(datetime.strptime(d, "%d %b %Y"))
            except ValueError:
                pass
        if parsed:
            parsed.sort()
            g["commence_date"]    = parsed[0].strftime("%Y-%m-%d")
            g["completion_date"]  = parsed[-1].strftime("%Y-%m-%d")
        else:
            g["commence_date"]   = None
            g["completion_date"] = None

    return groups


# ── Trainee fetching ──────────────────────────────────────────────────────────

def fetch_trainees_for_sessions(
    client: MomenceAPIClient,
    session_ids: List[str],
) -> List[Dict]:
    """
    Call get_session_bookings() for each session ID and return a deduplicated
    list of member dicts (keyed by member ID, non-cancelled bookings only).
    """
    seen_member_ids = set()
    trainees = []

    for sid in session_ids:
        try:
            sid_int = int(sid)
        except ValueError:
            log(f"  [WARN] Invalid session ID {sid!r}, skipping")
            continue

        page = 0
        while True:
            try:
                result = client.get_session_bookings(sid_int, page=page, page_size=BOOKINGS_PAGE_SIZE)
            except Exception as e:
                log(f"  [WARN] get_session_bookings({sid_int}, page={page}) failed: {e}")
                break

            bookings = result.get("payload", [])
            for b in bookings:
                # Skip cancelled bookings
                if b.get("cancelledAt"):
                    continue
                member = b.get("member") or {}
                mid = member.get("id")
                if mid and mid not in seen_member_ids:
                    seen_member_ids.add(mid)
                    trainees.append({
                        "momence_member_id": str(mid),
                        "first_name":  member.get("firstName") or "",
                        "last_name":   member.get("lastName") or "",
                        "email":       (member.get("email") or "").lower().strip(),
                        "phone":       member.get("phoneNumber") or "",
                        "photo_url":   member.get("pictureUrl") or "",
                        "enrolled_at": b.get("createdAt") or "",
                    })

            pagination = result.get("pagination", {})
            total = pagination.get("totalCount", 0)
            fetched_so_far = (page + 1) * BOOKINGS_PAGE_SIZE
            if fetched_so_far >= total or len(bookings) < BOOKINGS_PAGE_SIZE:
                break
            page += 1

    return trainees


# ── Supabase sync ─────────────────────────────────────────────────────────────

def get_or_create_teacher(trainee: Dict, discipline: str) -> Optional[str]:
    """
    Look up a teachers record by email. If found, optionally fill in missing
    phone/photo. If not found, create a new record with Student grade (1).
    Returns the teacher UUID, or None on failure.
    """
    email = trainee.get("email", "")
    if not email:
        log(f"  [WARN] Trainee has no email: {trainee.get('first_name')} {trainee.get('last_name')} — skipping")
        return None

    try:
        rows = sb_get("teachers", params={"email": f"eq.{email}", "select": "id,phone,photo_url"})
    except Exception as e:
        log(f"  [ERROR] Supabase lookup for email {email}: {e}")
        return None

    if rows:
        teacher_id = rows[0]["id"]
        # Fill in phone/photo if missing in Supabase but available from Momence
        updates = {}
        if not rows[0].get("phone") and trainee.get("phone"):
            updates["phone"] = trainee["phone"]
        if not rows[0].get("photo_url") and trainee.get("photo_url"):
            updates["photo_url"] = trainee["photo_url"]
        if updates:
            try:
                sb_patch("teachers", "id", teacher_id, updates)
                log(f"    Updated teacher {email}: {list(updates.keys())}")
            except Exception as e:
                log(f"  [WARN] Could not update teacher {email}: {e}")
        return teacher_id

    # Create new teacher record for this trainee
    grades = dict(DEFAULT_GRADES)
    grades[discipline] = 1  # Student grade in the relevant discipline

    new_teacher = {
        "first_name":    trainee["first_name"],
        "last_name":     trainee["last_name"],
        "email":         email,
        "phone":         trainee.get("phone") or None,
        "photo_url":     trainee.get("photo_url") or None,
        "home_location": None,
        "notes":         "Auto-created from Momence course enrolment",
        "grades":        grades,
        "locations":     [],
        "avail_days":    [],
        "avail_times":   [],
    }
    try:
        created = sb_post("teachers", new_teacher)
        teacher_id = created.get("id")
        log(f"    Created new teacher record: {email} (id={teacher_id})")
        return teacher_id
    except Exception as e:
        log(f"  [ERROR] Could not create teacher for {email}: {e}")
        return None


def sync_course_to_supabase(
    group: Dict,
    existing_courses: List[Dict],
) -> Optional[str]:
    """
    Match a course group to an existing training_courses record (by normalised
    name). If no match, insert a new record. Returns the course UUID.
    """
    norm = normalise_name(group["display_name"])
    now_iso = datetime.now(timezone.utc).isoformat()

    for existing in existing_courses:
        if normalise_name(existing.get("course_name", "")) == norm:
            course_id = existing["id"]
            # Update sync-managed fields only — preserve manually entered data
            updates = {
                "location":       group.get("location") or existing.get("location"),
                "status":         "active",
                "last_synced_at": now_iso,
            }
            if not existing.get("momence_id") and group["session_ids"]:
                updates["momence_id"] = group["session_ids"][0]
            if group.get("completion_date") and not existing.get("completion_date"):
                updates["completion_date"] = group["completion_date"]
            try:
                sb_patch("training_courses", "id", course_id, updates)
                log(f"  Updated existing course: {group['display_name']} (id={course_id})")
            except Exception as e:
                log(f"  [ERROR] Could not update course {group['display_name']}: {e}")
            return course_id

    # No match found — create new course
    if not group.get("commence_date"):
        log(f"  [WARN] Cannot create course {group['display_name']!r}: no commence_date derived")
        return None

    new_course = {
        "course_name":     group["display_name"],
        "commence_date":   group["commence_date"],
        "completion_date": group.get("completion_date"),
        "category":        group["discipline"],
        "location":        group.get("location"),
        "momence_id":      group["session_ids"][0] if group["session_ids"] else None,
        "status":          "active",
        "last_synced_at":  now_iso,
        "req_community_classes": 4,
    }
    try:
        created = sb_post("training_courses", new_course)
        course_id = created.get("id")
        log(f"  Created new course: {group['display_name']} (id={course_id})")
        return course_id
    except Exception as e:
        log(f"  [ERROR] Could not create course {group['display_name']}: {e}")
        return None


def sync_enrollment(
    teacher_id: str,
    course_id: str,
    trainee: Dict,
    existing_enrollments: List[Dict],
) -> bool:
    """
    Create a trainee_enrollments record if one doesn't already exist for
    (teacher_id, course_id). Returns True if created, False if already exists.
    """
    for enr in existing_enrollments:
        if enr.get("teacher_id") == teacher_id and enr.get("course_id") == course_id:
            return False  # already enrolled

    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "teacher_id":       teacher_id,
        "course_id":        course_id,
        "momence_member_id": trainee.get("momence_member_id"),
        "enrolled_at":      trainee.get("enrolled_at") or now_iso,
        "status":           "active",
        "classes_completed": 0,
        "last_synced_at":   now_iso,
    }
    try:
        sb_post("trainee_enrollments", record)
        return True
    except Exception as e:
        log(f"    [ERROR] Could not create enrollment teacher={teacher_id} course={course_id}: {e}")
        return False


# ── Master CSV writers ────────────────────────────────────────────────────────

def write_master_courses_csv(course_rows: List[Dict]) -> None:
    if not course_rows:
        return
    fieldnames = list(course_rows[0].keys())
    with open(MASTER_COURSES, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(course_rows)
    log(f"Written {len(course_rows)} courses to {Path(MASTER_COURSES).name}")


def write_master_trainees_csv(trainee_rows: List[Dict]) -> None:
    if not trainee_rows:
        return
    fieldnames = list(trainee_rows[0].keys())
    with open(MASTER_TRAINEES, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trainee_rows)
    log(f"Written {len(trainee_rows)} trainee records to {Path(MASTER_TRAINEES).name}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ts = datetime.now().strftime("%Y %m %d %H %M")
    setup_logging(ts)
    batch_log("momence_courses_sync.py started")
    log("=" * 60)
    log("Momence Courses Sync")
    log(f"Run: {ts}")
    log("=" * 60)

    # Validate Supabase config
    if not SUPABASE_URL or not SERVICE_ROLE_KEY:
        msg = "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in .env"
        log(f"[ERROR] {msg}")
        batch_log(f"ERROR: momence_courses_sync.py — {msg}")
        sys.exit(1)

    # ── Step 1: Read classes CSV and identify courses ─────────────────────────
    log("\n[Step 1] Reading classes CSV and identifying courses...")
    try:
        rows = read_latest_classes_csv()
    except FileNotFoundError as e:
        log(f"[ERROR] {e}")
        batch_log(f"ERROR: momence_courses_sync.py — {e}")
        sys.exit(1)

    log(f"Total rows in CSV: {len(rows)}")
    course_groups = group_courses(rows)
    log(f"Courses identified: {len(course_groups)}")
    for key, g in course_groups.items():
        log(f"  {g['display_name']!r}: {len(g['session_ids'])} sessions, "
            f"commence={g.get('commence_date')}, complete={g.get('completion_date')}")

    if not course_groups:
        log("[INFO] No courses found matching COURSE_KEYWORDS. "
            "If this is unexpected, check the keyword list at the top of this script.")
        batch_log("momence_courses_sync.py completed OK — 0 courses found")
        return

    # ── Step 2: Load existing Supabase data ───────────────────────────────────
    log("\n[Step 2] Loading existing Supabase data...")
    try:
        existing_courses     = sb_get("training_courses",     {"select": "*"})
        existing_enrollments = sb_get("trainee_enrollments",  {"select": "*"})
        log(f"  training_courses in Supabase    : {len(existing_courses)}")
        log(f"  trainee_enrollments in Supabase : {len(existing_enrollments)}")
    except Exception as e:
        log(f"[ERROR] Could not load Supabase data: {e}")
        batch_log(f"ERROR: momence_courses_sync.py — Supabase load failed: {e}")
        sys.exit(1)

    # ── Step 3: Authenticate Momence API ──────────────────────────────────────
    log("\n[Step 3] Authenticating with Momence API...")
    try:
        client = MomenceAPIClient()
        client.authenticate()
    except Exception as e:
        log(f"[ERROR] Momence authentication failed: {e}")
        batch_log(f"ERROR: momence_courses_sync.py — Momence auth failed: {e}")
        sys.exit(1)

    # ── Step 4: Sync each course ──────────────────────────────────────────────
    csv_course_rows   = []
    csv_trainee_rows  = []
    total_new_courses = 0
    total_new_enr     = 0
    total_trainees    = 0

    for key, group in course_groups.items():
        log(f"\n[Course] {group['display_name']!r}")

        # 4a. Sync course to Supabase
        course_id = sync_course_to_supabase(group, existing_courses)
        if not course_id:
            log(f"  [SKIP] Could not get/create Supabase record for this course.")
            continue

        csv_course_rows.append({
            "course_name":     group["display_name"],
            "discipline":      group["discipline"],
            "location":        group["location"],
            "commence_date":   group.get("commence_date") or "",
            "completion_date": group.get("completion_date") or "",
            "session_count":   len(group["session_ids"]),
            "supabase_id":     course_id,
            "synced_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        # 4b. Fetch trainees for all sessions of this course
        log(f"  Fetching trainees for {len(group['session_ids'])} session(s)...")
        trainees = fetch_trainees_for_sessions(client, group["session_ids"])
        log(f"  Unique trainees found: {len(trainees)}")
        total_trainees += len(trainees)

        # 4c. Sync each trainee
        for trainee in trainees:
            log(f"  Trainee: {trainee['first_name']} {trainee['last_name']} <{trainee['email']}>")

            teacher_id = get_or_create_teacher(trainee, group["discipline"])
            if not teacher_id:
                continue

            created = sync_enrollment(teacher_id, course_id, trainee, existing_enrollments)
            if created:
                total_new_enr += 1
                log(f"    -> Enrolled (new)")
                # Add to local list to avoid duplicates within this run
                existing_enrollments.append({
                    "teacher_id": teacher_id,
                    "course_id":  course_id,
                })
            else:
                log(f"    -> Already enrolled (skipped)")

            csv_trainee_rows.append({
                "course_name":       group["display_name"],
                "supabase_course_id": course_id,
                "momence_member_id": trainee["momence_member_id"],
                "first_name":        trainee["first_name"],
                "last_name":         trainee["last_name"],
                "email":             trainee["email"],
                "phone":             trainee.get("phone") or "",
                "photo_url":         trainee.get("photo_url") or "",
                "enrolled_at":       trainee.get("enrolled_at") or "",
                "supabase_teacher_id": teacher_id,
                "synced_at":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

    # ── Step 5: Write master CSVs ─────────────────────────────────────────────
    log("\n[Step 5] Writing master CSV files...")
    write_master_courses_csv(csv_course_rows)
    write_master_trainees_csv(csv_trainee_rows)

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = (
        f"momence_courses_sync.py completed OK — "
        f"{len(course_groups)} courses, "
        f"{total_trainees} trainees, "
        f"{total_new_enr} new enrollments"
    )
    log(f"\n{'='*60}\n{summary}\n{'='*60}")
    batch_log(summary)


if __name__ == "__main__":
    main()
