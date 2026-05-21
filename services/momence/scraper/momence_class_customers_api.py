#!/usr/bin/env python3
"""
momence_class_customers_api.py
===============================
API-based replacement for momence_class_customers_scrape_1 all.py
(Selenium, Step 8 — previously 60–80 minutes for ~470 classes).

Reads:
    momence_all_classes_*.csv   (latest file, produced by extract_all_classes_1.py)

Writes:
    Momence_class_customers_all_<YYYY MM DD HH MM>.csv   — dated snapshot
    Momence_class_customers_combined.csv                  — cumulative, deduped

Output columns:
    Class Number, Class Name, Input Timestamp, Customer Name,
    Email, Signup Time, Checked In, Cancelled At, Payment Method

Notes:
  - Payment Method is left blank for API-sourced rows.  It is already
    present in master_bookings.csv (populated by Momence_bookings_update.py).
  - Email, Checked In, and Cancelled At are new fields not available in
    the old Selenium scraper.
  - Deduplication key: Class Number + Customer Name + Signup Time.
    Newer rows overwrite older ones in the combined file.
"""

import csv
import glob
import logging
import os
import re
import sys
import time
from datetime import datetime
from typing import List, Dict, Any

import requests

from momence_api_client import MomenceAPIClient

# ── Configuration ─────────────────────────────────────────────────────────────
PAGE_SIZE      = 100   # max for /host/sessions/{id}/bookings
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
# Master batch log — moved out of OneDrive on 2026-05-18 to stop sync locks
# truncating writes. Falls back to the legacy in-tree path if the local
# folder is absent (e.g. clean checkout on a new machine).
_LOCAL_BATCH_LOG_DIR = r"C:\Users\markj\Momence_local_logs"
if os.path.isdir(_LOCAL_BATCH_LOG_DIR):
    BATCH_LOG_FILE = os.path.join(_LOCAL_BATCH_LOG_DIR, "Momence_batch_log.txt")
else:
    BATCH_LOG_FILE = os.path.join(SCRIPT_DIR, "Log_files", "Momence_batch_log.txt")
COMBINED_FILE  = "Momence_class_customers_combined.csv"
LOG_DIR        = "Log_files"

# Maximum acceptable failure rate before the script exits non-zero.
# Failures at or below this fraction are treated as transient API errors
# (e.g. a single 502) and the script exits 0 so the chain continues cleanly.
# Failures above this threshold indicate a systemic problem (auth failure,
# bulk 5xx) and exit 1 so the chain marks the step as failed.
FAILURE_TOLERANCE  = 0.05  # 5 % of classes
MAX_RETRIES        = 3     # retries per page on HTTP 5xx errors
RETRY_DELAY_SECS   = 45   # seconds to wait between retries

OUTPUT_HEADERS = [
    "Class Number", "Class Name", "Input Timestamp",
    "Customer Name", "Email", "Signup Time",
    "Checked In", "Cancelled At", "Payment Method",
]

DEDUP_KEY = lambda r: (r["Class Number"], r["Customer Name"], r["Signup Time"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def setup_logging(timestamp_str: str) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        filename=f"{LOG_DIR}/momence_class_customers_api_{timestamp_str}.txt",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )


def append_to_batch_log(message: str) -> None:
    """Append a timestamped line to Momence_batch_log.txt with retry."""
    os.makedirs(os.path.dirname(BATCH_LOG_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} - {message}\n"
    for attempt in range(3):
        try:
            with open(BATCH_LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(line)
            return
        except Exception as exc:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"[BATCH LOG WRITE FAILED after 3 attempts: {exc}] {line.rstrip()}", file=sys.stderr)


def log(msg: str) -> None:
    print(msg)
    logging.info(msg)


def parse_iso(value: str) -> str:
    """Return a human-readable datetime string from an ISO-8601 value, or 'NA'."""
    if not value:
        return "NA"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%a, %d %b %Y %H:%M")
    except ValueError:
        return value   # return raw if unparseable


def find_latest_file(pattern: str) -> str:
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No file matching '{pattern}' found.")
    return max(files, key=os.path.getmtime)


def load_class_list(path: str):
    """Return (input_timestamp_str, [{'class_number': str, 'class_name': str}])."""
    match = re.search(r'_(\d{4} \d{2} \d{2} \d{2} \d{2})\.csv$', os.path.basename(path))
    input_ts = match.group(1) if match else datetime.now().strftime("%Y %m %d %H %M")
    classes = []
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            num  = row.get("Class Number", "").strip()
            name = row.get("Class Name", "").strip()
            if num and num.isdigit():
                classes.append({"class_number": num, "class_name": name})
    return input_ts, classes


def fetch_bookings(client: MomenceAPIClient, session_id: int) -> List[Dict[str, Any]]:
    """Fetch all bookings for one session, handling pagination automatically.

    Transient HTTP 5xx errors (e.g. 502 Bad Gateway) on any page are retried
    up to MAX_RETRIES times with a RETRY_DELAY_SECS wait between attempts.
    """
    all_bookings: list = []
    page = 0
    while True:
        # -- Per-page retry loop for transient server errors ------------------
        result = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = client.get_session_bookings(session_id=session_id,
                                                      page=page, page_size=PAGE_SIZE)
                break  # success — exit retry loop
            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status is not None and status >= 500:
                    if attempt < MAX_RETRIES:
                        logging.warning(
                            "Session %s page %s: HTTP %s — retrying in %ss "
                            "(attempt %s of %s)",
                            session_id, page, status, RETRY_DELAY_SECS,
                            attempt, MAX_RETRIES,
                        )
                        time.sleep(RETRY_DELAY_SECS)
                    else:
                        logging.error(
                            "Session %s page %s: HTTP %s — all %s attempts exhausted",
                            session_id, page, status, MAX_RETRIES,
                        )
                        raise
                else:
                    raise  # non-5xx error — don't retry
        # ---------------------------------------------------------------------
        payload = result.get("payload", [])
        if not payload:
            break
        all_bookings.extend(payload)
        total = result.get("pagination", {}).get("totalCount", 0)
        if len(all_bookings) >= total or len(payload) < PAGE_SIZE:
            break
        page += 1
    return all_bookings


def booking_to_row(booking: dict, class_number: str,
                   class_name: str, input_ts: str) -> dict:
    member   = booking.get("member") or {}
    first    = (member.get("firstName") or "").strip()
    last     = (member.get("lastName")  or "").strip()
    name     = f"{first} {last}".strip() or "NA"
    email    = (member.get("email") or "").strip()

    return {
        "Class Number":    class_number,
        "Class Name":      class_name,
        "Input Timestamp": input_ts,
        "Customer Name":   name,
        "Email":           email,
        "Signup Time":     parse_iso(booking.get("createdAt", "")),
        "Checked In":      "Yes" if booking.get("checkedIn") else "No",
        "Cancelled At":    parse_iso(booking.get("cancelledAt", "")),
        "Payment Method":  "",   # not in API; already in master_bookings.csv
    }


def update_combined(new_rows: list) -> int:
    """Merge new_rows into COMBINED_FILE using DEDUP_KEY. Returns total row count."""
    existing: dict = {}
    if os.path.exists(COMBINED_FILE):
        with open(COMBINED_FILE, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                # Ensure all output columns exist (handles old schema rows gracefully)
                normalised = {col: row.get(col, "") for col in OUTPUT_HEADERS}
                existing[DEDUP_KEY(normalised)] = normalised

    for row in new_rows:
        existing[DEDUP_KEY(row)] = row   # new data wins

    with open(COMBINED_FILE, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerows(existing.values())

    return len(existing)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    now           = datetime.now()
    timestamp_str = now.strftime("%Y %m %d %H %M")
    dated_output  = f"Momence_class_customers_all_{timestamp_str}.csv"

    setup_logging(timestamp_str)
    append_to_batch_log("momence_class_customers_api.py started")

    # Load class list
    try:
        input_file = find_latest_file("momence_all_classes_*.csv")
        log(f"[INFO] Input  : {input_file}")
        input_ts, classes = load_class_list(input_file)
        log(f"[INFO] Classes: {len(classes)}  (timestamp {input_ts})")
    except Exception as exc:
        log(f"[ERROR] Could not load input: {exc}")
        append_to_batch_log(f"ERROR: momence_class_customers_api.py — {exc}")
        sys.exit(1)

    if not classes:
        log("[WARN] No classes in input file. Exiting.")
        append_to_batch_log("momence_class_customers_api.py: no classes found, exiting")
        sys.exit(0)

    # Authenticate
    try:
        client = MomenceAPIClient()
        client.authenticate()
    except Exception as exc:
        log(f"[ERROR] Auth failed: {exc}")
        append_to_batch_log(f"ERROR: momence_class_customers_api.py auth — {exc}")
        sys.exit(1)

    # Fetch bookings for every class
    all_rows:      list = []
    failed_ids:    list = []

    for i, cls in enumerate(classes, 1):
        num  = cls["class_number"]
        name = cls["class_name"]
        try:
            bookings = fetch_bookings(client, int(num))
            rows     = [booking_to_row(b, num, name, input_ts) for b in bookings]
            all_rows.extend(rows)
            log(f"[{i:>4}/{len(classes)}] {num:>8}  {name[:40]:<40}  {len(bookings):>3} bookings")
        except Exception as exc:
            log(f"[{i:>4}/{len(classes)}] FAILED {num}: {exc}")
            logging.error(f"Failed class {num}: {exc}", exc_info=True)
            failed_ids.append(num)

    # Write dated snapshot
    with open(dated_output, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerows(all_rows)
    log(f"[OK] {len(all_rows)} rows -> {dated_output}")

    # Update combined file
    combined_total = update_combined(all_rows)
    log(f"[OK] Combined file: {combined_total} total rows -> {COMBINED_FILE}")

    # Summary and exit code
    failure_rate   = len(failed_ids) / len(classes) if classes else 0
    tolerable      = failure_rate <= FAILURE_TOLERANCE
    exit_code      = 0 if tolerable else 1

    summary = (f"momence_class_customers_api.py complete: "
               f"{len(classes)} classes, {len(all_rows)} customer rows, "
               f"{len(failed_ids)} failures")
    log(f"\n[SUMMARY] {summary}")

    if failed_ids:
        log(f"[WARN] Failed class IDs: {', '.join(failed_ids)}")
        if tolerable:
            log(
                f"[INFO] Failure rate {failure_rate:.1%} is within the "
                f"{FAILURE_TOLERANCE:.0%} tolerance — exiting OK"
            )
        else:
            log(
                f"[ERROR] Failure rate {failure_rate:.1%} exceeds the "
                f"{FAILURE_TOLERANCE:.0%} tolerance — exiting with error"
            )

    append_to_batch_log(
        summary + (f" — {len(failed_ids)} tolerated" if failed_ids and tolerable else "")
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
