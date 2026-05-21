#!/usr/bin/env python3
"""
momence_sessions_api.py
=======================
API-based replacement for momence_scraper8.py (Selenium, Step 1).

Fetches the Momence class schedule via the v2 REST API instead of
paging through the browser UI.  Produces identically-named output files
so that all downstream scripts (extract_full_classes2.py,
extract_all_classes_1.py) work without any modification.

Usage (drop-in replacement for momence_scraper8.py):
    python momence_sessions_api.py p      # past classes
    python momence_sessions_api.py f      # future/upcoming classes
    python momence_sessions_api.py p 150  # page-count arg is silently ignored

Output:
    momence_classes_p_<YYYY MM DD HH MM>.csv   (past mode)
    momence_classes_f_<YYYY MM DD HH MM>.csv   (future mode)

Columns (identical to momence_scraper8.py output):
    Timestamp, Class Name, Class Number, Weekday, Date, Time,
    Class Full Name, Teacher, Substitute, Location, Signups,
    Capacity, Waitlist, Checked In

Notes:
  - Teacher, Substitute, Waitlist, Checked In are written as "NA":
    the /host/sessions LIST endpoint does not return these fields.
    Teacher data IS available via the per-session detail endpoint
        GET /api/v2/host/sessions/{id}
    which returns `teacher`, `originalTeacher`, and `additionalTeachers`
    objects.  The companion script backfill_teacher.py uses that
    endpoint to populate Teacher / Teacher ID / Substitute /
    Substitute ID after this script has run.  Substitute is detected by
    comparing teacher.id against originalTeacher.id (different ids =>
    substitution).  Ritual does not currently use additionalTeachers
    (assistant teachers); that field is always null and is intentionally
    ignored.
  - Authentication uses .env credentials (MOMENCE_CLIENT_ID etc.)
    rather than the hardcoded email/password in the old scraper.
  - Past mode fetches the last PAST_DAYS_LOOKBACK days (default 180).
  - Future mode fetches the next FUTURE_DAYS_AHEAD days (default 180).
  - Supabase note: any teachers table that mirrors Momence staff should
    persist the Momence teacher.id (e.g. as `momence_teacher_id`) so
    bookings, sessions and class-customer rows can be joined to a
    canonical teacher record.  momence_courses_sync.py currently joins
    on email; the Momence id is a more stable key.
"""

import csv
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from momence_api_client import MomenceAPIClient
from momence_teacher_utils import (
    extract_teacher_info,
    fetch_session_detail,
)

# ── Timezone ──────────────────────────────────────────────────────────────────
# Queensland observes AEST (UTC+10) year-round — no daylight saving.
BRISBANE_TZ = ZoneInfo("Australia/Brisbane")

# ── Configuration ─────────────────────────────────────────────────────────────
PAST_DAYS_LOOKBACK = 180   # days back for 'p' mode
FUTURE_DAYS_AHEAD  = 180   # days forward for 'f' mode
PAGE_SIZE          = 200   # max allowed by Momence API for /host/sessions
ENRICH_SLEEP_SECS  = 0.10  # delay between per-session detail GETs
# Use __file__-relative path so the batch log is always found regardless of
# the process working directory (e.g. when invoked by Task Scheduler with a
# different "Start In" folder, or when OneDrive changes the sync path).
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
# Master batch log — moved out of OneDrive on 2026-05-18 to stop sync locks
# truncating writes. Falls back to the legacy in-tree path if the local
# folder is absent (e.g. clean checkout on a new machine).
_LOCAL_BATCH_LOG_DIR = r"C:\Users\markj\Momence_local_logs"
if os.path.isdir(_LOCAL_BATCH_LOG_DIR):
    BATCH_LOG_FILE = os.path.join(_LOCAL_BATCH_LOG_DIR, "Momence_batch_log.txt")
else:
    BATCH_LOG_FILE = os.path.join(SCRIPT_DIR, "Log_files", "Momence_batch_log.txt")
MAX_RETRIES        = 3     # retries per page on HTTP 5xx errors
RETRY_DELAY_SECS   = 45   # seconds to wait between retries

# Column order matches the legacy scraper output, with Teacher ID and
# Substitute ID inserted alongside their name columns.  The enrichment
# pass below populates all four; without enrichment they would be "NA".
HEADERS = [
    "Timestamp", "Class Name", "Class Number", "Weekday", "Date", "Time",
    "Class Full Name",
    "Teacher", "Teacher ID", "Substitute", "Substitute ID",
    "Location",
    "Signups", "Capacity", "Waitlist", "Checked In",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def setup_logging(which: str, timestamp_str: str) -> None:
    os.makedirs("Log_files", exist_ok=True)
    logging.basicConfig(
        filename=f"Log_files/momence_sessions_api_{which}_{timestamp_str}.txt",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )


def append_to_batch_log(message: str) -> None:
    """Append a timestamped line to Momence_batch_log.txt.

    Retries up to 6 times with a 5-second delay (30 s max) to survive
    OneDrive sync locks.  Falls back to stderr so the message is
    captured in the chain log even when the file is inaccessible.
    """
    os.makedirs(os.path.dirname(BATCH_LOG_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} - {message}\n"
    for attempt in range(6):
        try:
            with open(BATCH_LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(line)
            return
        except Exception as exc:
            if attempt < 5:
                time.sleep(5)
            else:
                print(f"[BATCH LOG WRITE FAILED after 6 attempts: {exc}] {line.rstrip()}", file=sys.stderr)


def log(msg: str) -> None:
    print(msg)
    logging.info(msg)


def parse_iso(value: str) -> Optional[datetime]:
    """Parse an ISO-8601 datetime string, handling both Z and ±HH:MM offsets."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def session_to_row(session: dict, run_timestamp: str) -> dict:
    """Map one API session object to a CSV row matching the scraper column layout."""
    # Convert UTC API timestamps to AEST before extracting date/time strings.
    # The Momence API returns UTC (Z suffix). Without this conversion, morning
    # AEST classes appear on the previous UTC day with wrong times — causing
    # ghost classes in the dashboard that cannot be matched to booking records.
    starts_at_utc = parse_iso(session.get("startsAt", ""))
    ends_at_utc   = parse_iso(session.get("endsAt", ""))
    starts_at = starts_at_utc.astimezone(BRISBANE_TZ) if starts_at_utc else None
    ends_at   = ends_at_utc.astimezone(BRISBANE_TZ)   if ends_at_utc   else None

    weekday = date_str = time_str = "NA"
    if starts_at:
        weekday  = starts_at.strftime("%a")
        date_str = starts_at.strftime("%d %b %Y")
        t_start  = starts_at.strftime("%H:%M")
        t_end    = ends_at.strftime("%H:%M") if ends_at else ""
        time_str = f"{t_start} - {t_end}" if t_end else t_start

    loc = session.get("inPersonLocation") or {}
    location = loc.get("name") or "NA"

    name     = session.get("name") or "NA"
    class_id = str(session.get("id", "NA"))
    signups  = str(session.get("bookingCount", 0))
    capacity = str(session.get("capacity", "NA")) if session.get("capacity") is not None else "NA"

    # Teacher info comes from the per-session enrichment pass (see
    # enrich_with_teachers below).  If the lookup failed for this row,
    # the values fall back to "NA" so downstream scripts still see the
    # expected schema.
    info = session.get("_teacher_info") or {}
    teacher       = info.get("teacher_name")    or "NA"
    teacher_id    = info.get("teacher_id")      or "NA"
    substitute    = info.get("substitute_name") or "NA"
    substitute_id = info.get("substitute_id")   or "NA"

    return {
        "Timestamp":      run_timestamp,
        "Class Name":     name,
        "Class Number":   class_id,
        "Weekday":        weekday,
        "Date":           date_str,
        "Time":           time_str,
        "Class Full Name": name,   # API does not split name/full-name
        "Teacher":        teacher,
        "Teacher ID":     teacher_id,
        "Substitute":     substitute,
        "Substitute ID":  substitute_id,
        "Location":       location,
        "Signups":        signups,
        "Capacity":       capacity,
        "Waitlist":       "NA",    # not available via sessions list endpoint
        "Checked In":     "NA",    # not available via sessions list endpoint
    }


def _page_date_bounds(payload: list):
    """Return (min_date, max_date) of AEST startsAt dates across a page payload.

    Returns (None, None) if no parseable dates are found.
    """
    dates = []
    for s in payload:
        dt = parse_iso(s.get("startsAt", ""))
        if dt:
            dates.append(dt.astimezone(BRISBANE_TZ).date())
    if not dates:
        return None, None
    return min(dates), max(dates)


def _find_range_start_page(
    client: MomenceAPIClient,
    start_date,
    total_count: int,
) -> int:
    """Binary-search for the first page whose sessions reach or exceed start_date.

    Called when the API is detected to be sorting sessions ascending
    (oldest-first), which causes the main fetch loop to scan hundreds of
    pre-range pages before finding any in-range sessions.  The binary search
    locates the approximate starting page in O(log N) probes instead of the
    O(N) sequential scan, reducing runtime from ~90 min to ~20 min for a
    56,000-session corpus.

    Returns the page number to begin the main scan from.  This may be one or
    two pages before the true first in-range page; the caller collects all
    in-range sessions while scanning forward, so a small undershoot is safe.
    Overshooting (returning a page after the range) cannot occur: the binary
    search always returns the *lowest* page where max_date >= start_date.
    """
    if total_count <= 0:
        return 0
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
    lo, hi = 0, total_pages - 1

    log(f"  [SKIP] API is sorting ascending — binary-searching for start_date "
        f"{start_date} across ~{total_pages} pages ...")

    probes = 0
    while lo < hi:
        mid = (lo + hi) // 2
        probes += 1
        try:
            result = client.get_sessions(page=mid, page_size=PAGE_SIZE)
            payload = result.get("payload", [])
        except Exception:  # noqa: BLE001
            # If the probe request fails, conservatively narrow to the lower half
            # so we do not skip past the range.
            hi = mid
            continue

        _, page_max = _page_date_bounds(payload)
        if page_max is None:
            # No parseable dates — treat as pre-range and search higher.
            lo = mid + 1
            continue

        if page_max < start_date:
            lo = mid + 1   # entire page is before the range — search higher
        else:
            hi = mid       # page may contain or precede the range start

    log(f"  [SKIP] Binary search done ({probes} probes) — main scan starts at page {lo}.")
    return lo


def fetch_all_sessions(client: MomenceAPIClient, start_date, end_date) -> list:
    """Fetch every session in the date range, paging through the API.

    NOTE: The Momence v2 API ignores startDate/endDate query parameters and
    returns all sessions regardless of the requested range.  We therefore
    apply a client-side date filter after each page is received so that the
    output CSV contains only sessions whose startsAt falls within
    [start_date, end_date].

    Sort-direction handling
    -----------------------
    The API has been observed to change sort order between runs:

    * Descending (newest-first): page 0 has the most recent sessions.
      The in-range window is found immediately; scanning stops when a full
      page falls before start_date.

    * Ascending (oldest-first, observed from 2026-05-09): page 0 has the
      oldest sessions.  Without intervention the script scans ~230 empty
      pages before reaching the 180-day window.  On detecting ascending
      order, _find_range_start_page() binary-searches for the approximate
      first in-range page, cutting the pre-range scan from ~230 pages to
      ~8 probe pages.

    Post-range early exit
    ---------------------
    Once every session on a fetched page starts after end_date, scanning
    stops regardless of sort direction.  This saves ~30 post-range pages
    when the API sorts ascending.

    Transient HTTP 5xx errors (e.g. 502 Bad Gateway) on any page are retried
    up to MAX_RETRIES times with a RETRY_DELAY_SECS wait between attempts.
    """
    all_sessions = []
    page = 0
    sort_check_done = False  # only run the ascending-sort detection once

    while True:
        # ── Per-page retry loop for transient server errors ────────────────
        result = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = client.get_sessions(
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.min.time()),
                    page=page,
                    page_size=PAGE_SIZE,
                )
                break  # success — exit retry loop
            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status is not None and status >= 500:
                    if attempt < MAX_RETRIES:
                        log(f"  Page {page}: HTTP {status} — retrying in {RETRY_DELAY_SECS}s "
                            f"(attempt {attempt} of {MAX_RETRIES})")
                        time.sleep(RETRY_DELAY_SECS)
                    else:
                        log(f"  Page {page}: HTTP {status} — all {MAX_RETRIES} attempts "
                            f"exhausted, aborting")
                        raise
                else:
                    raise  # non-5xx error — don't retry
        # ──────────────────────────────────────────────────────────────────

        payload = result.get("payload", [])
        if not payload:
            break

        pagination  = result.get("pagination", {})
        total       = pagination.get("totalCount", 0)

        # ── Ascending-sort detection and page skip (runs once, on page 0) ──
        # If the first page contains only sessions before start_date, the API
        # is sorting oldest-first.  Binary-search for the approximate first
        # in-range page to avoid scanning hundreds of pre-range pages.
        if not sort_check_done:
            sort_check_done = True
            _, page_max = _page_date_bounds(payload)
            if page_max is not None and page_max < start_date:
                skip_to = _find_range_start_page(client, start_date, total)
                if skip_to > page:
                    page = skip_to
                    continue  # re-enter loop at the binary-searched page
        # ──────────────────────────────────────────────────────────────────

        # ── Post-range early exit ──────────────────────────────────────────
        # If every session on this page starts after end_date, we have passed
        # the target window — no more in-range sessions will be found.
        page_min, _ = _page_date_bounds(payload)
        if page_min is not None and page_min > end_date:
            log(f"  Page {page}: earliest session {page_min} > end_date {end_date} "
                f"— stopping (past end of date range).")
            break
        # ──────────────────────────────────────────────────────────────────

        # Client-side date filter -- the API does not honour startDate/endDate.
        # Compare using the AEST date so that early-morning classes (which fall
        # on the previous UTC day) are still included in the correct local day.
        in_range = []
        for s in payload:
            dt = parse_iso(s.get("startsAt", ""))
            if dt:
                dt_aest = dt.astimezone(BRISBANE_TZ)
                if start_date <= dt_aest.date() <= end_date:
                    in_range.append(s)
        all_sessions.extend(in_range)

        log(f"  Page {page}: {len(payload)} fetched, {len(in_range)} in range  (kept {len(all_sessions)} / {total})")

        if len(payload) < PAGE_SIZE:
            break
        page += 1

    return all_sessions


def enrich_with_teachers(client: MomenceAPIClient, sessions: list) -> int:
    """For each session, fetch /sessions/{id} and attach teacher info.

    Mutates each session dict by setting `_teacher_info` to a dict
    containing teacher_name, teacher_id, substitute_name and
    substitute_id.  Failures are logged and the session keeps an empty
    info dict so downstream code can fall back to "NA".

    Returns the number of sessions for which the lookup succeeded with
    a non-empty teacher name.
    """
    success = 0
    failures: list = []
    total = len(sessions)
    log(f"[INFO] Enriching {total} sessions with teacher info "
        f"(per-session GETs, ~{total * ENRICH_SLEEP_SECS:.0f}s minimum)")

    for i, s in enumerate(sessions, 1):
        sid = s.get("id")
        if sid is None:
            s["_teacher_info"] = {}
            continue
        try:
            detail = fetch_session_detail(client, sid)
            info   = extract_teacher_info(detail)
            s["_teacher_info"] = info
            if info.get("teacher_name"):
                success += 1
        except Exception as exc:  # noqa: BLE001
            s["_teacher_info"] = {}
            failures.append((sid, str(exc)))
            log(f"  Session {sid}: teacher lookup failed: {exc}")

        if i % 100 == 0 or i == total:
            log(f"  Enrichment: {i}/{total}  (filled so far: {success})")
        time.sleep(ENRICH_SLEEP_SECS)

    if failures:
        log(f"[WARN] Teacher enrichment failed for {len(failures)} session(s).")
    return success


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    which = "f"
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("p", "f"):
        which = sys.argv[1].lower()
    # argv[2] (page count) is accepted but ignored — we use date ranges instead

    now           = datetime.now()
    timestamp_str = now.strftime("%Y %m %d %H %M")
    run_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    output_file   = f"momence_classes_{which}_{timestamp_str}.csv"
    label         = "past" if which == "p" else "future"

    setup_logging(which, timestamp_str)
    append_to_batch_log(f"momence_sessions_api.py started — fetching {label} sessions")
    log(f"[INFO] Mode   : {label}")
    log(f"[INFO] Output : {output_file}")


    # Date range
    today = now.date()
    if which == "p":
        start_date = today - timedelta(days=PAST_DAYS_LOOKBACK)
        end_date   = today - timedelta(days=1)
    else:
        start_date = today
        end_date   = today + timedelta(days=FUTURE_DAYS_AHEAD)
    log(f"[INFO] Date range: {start_date} -> {end_date}")

    # Authenticate
    try:
        client = MomenceAPIClient()
        client.authenticate()
    except Exception as exc:
        msg = f"Authentication failed: {exc}"
        log(f"[ERROR] {msg}")
        append_to_batch_log(f"ERROR: momence_sessions_api.py — {msg}")
        sys.exit(1)

    # Fetch
    try:
        sessions = fetch_all_sessions(client, start_date, end_date)
    except Exception as exc:
        msg = f"Failed to fetch sessions: {exc}"
        log(f"[ERROR] {msg}")
        append_to_batch_log(f"ERROR: momence_sessions_api.py — {msg}")
        sys.exit(1)

    log(f"[INFO] Total sessions fetched: {len(sessions)}")

    # Enrich each session with teacher / substitute info via the
    # per-session detail endpoint (the list endpoint always returns
    # null teachers).  This adds one API call per session — see
    # ENRICH_SLEEP_SECS at the top of the file to tune the rate.
    try:
        filled = enrich_with_teachers(client, sessions)
        log(f"[INFO] Teacher info populated for {filled}/{len(sessions)} sessions")
    except Exception as exc:  # noqa: BLE001
        # Don't abort the whole run — a partial CSV is still valuable.
        log(f"[WARN] Enrichment pass aborted early: {exc}")
        append_to_batch_log(f"WARN: momence_sessions_api.py — enrichment aborted: {exc}")

    # Write CSV
    rows = [session_to_row(s, run_timestamp) for s in sessions]
    with open(output_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    msg = (f"momence_sessions_api.py complete: {len(rows)} {label} sessions "
           f"written to {output_file}")
    log(f"[OK] {msg}")
    append_to_batch_log(msg)


if __name__ == "__main__":
    main()
