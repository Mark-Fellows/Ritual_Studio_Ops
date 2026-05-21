#!/usr/bin/env python3
"""
momence_class_customers_full_api.py
=====================================
API-based replacement for momence_class_customers_scrape_4.py (Selenium, Step 3).

Reads:
    momence_full_classes_*.csv   (latest file, produced by extract_full_classes2.py)
    — contains only fully booked classes (Signups == Capacity).

Writes:
    Momence_class_customers_all_<YYYY MM DD HH MM>.csv   — dated snapshot
    Momence_class_customers_combined.csv                  — cumulative, deduped

This script is functionally identical to momence_class_customers_api.py
(Step 8) but operates on the full-classes subset rather than all classes.
Both scripts share the same output files and deduplication logic, so
running one after the other is safe.

Output columns:
    Class Number, Class Name, Input Timestamp, Customer Name,
    Email, Signup Time, Checked In, Cancelled At, Payment Method
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

from momence_api_client import MomenceAPIClient

# ── Configuration ─────────────────────────────────────────────────────────────
PAGE_SIZE      = 100
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

OUTPUT_HEADERS = [
    "Class Number", "Class Name", "Input Timestamp",
    "Customer Name", "Email", "Signup Time",
    "Checked In", "Cancelled At", "Payment Method",
]

DEDUP_KEY = lambda r: (r["Class Number"], r["Customer Name"], r["Signup Time"])


# ── Helpers (duplicated from momence_class_customers_api.py for standalone use)

def setup_logging(timestamp_str: str) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        filename=f"{LOG_DIR}/momence_class_customers_full_api_{timestamp_str}.txt",
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
    if not value:
        return "NA"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%a, %d %b %Y %H:%M")
    except ValueError:
        return value


def find_latest_file(pattern: str) -> str:
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No file matching '{pattern}' found.")
    return max(files, key=os.path.getmtime)


def load_class_list(path: str):
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


def fetch_bookings(client: MomenceAPIClient, session_id: int) -> list:
    all_bookings: list = []
    page = 0
    while True:
        result  = client.get_session_bookings(session_id=session_id,
                                               page=page, page_size=PAGE_SIZE)
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
    member = booking.get("member") or {}
    first  = (member.get("firstName") or "").strip()
    last   = (member.get("lastName")  or "").strip()
    name   = f"{first} {last}".strip() or "NA"
    return {
        "Class Number":    class_number,
        "Class Name":      class_name,
        "Input Timestamp": input_ts,
        "Customer Name":   name,
        "Email":           (member.get("email") or "").strip(),
        "Signup Time":     parse_iso(booking.get("createdAt", "")),
        "Checked In":      "Yes" if booking.get("checkedIn") else "No",
        "Cancelled At":    parse_iso(booking.get("cancelledAt", "")),
        "Payment Method":  "",
    }


def update_combined(new_rows: list) -> int:
    existing: dict = {}
    if os.path.exists(COMBINED_FILE):
        with open(COMBINED_FILE, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                normalised = {col: row.get(col, "") for col in OUTPUT_HEADERS}
                existing[DEDUP_KEY(normalised)] = normalised
    for row in new_rows:
        existing[DEDUP_KEY(row)] = row
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
    append_to_batch_log("momence_class_customers_full_api.py started")

    # Load full-classes input file
    try:
        input_file = find_latest_file("momence_full_classes_*.csv")
        log(f"[INFO] Input  : {input_file}")
        input_ts, classes = load_class_list(input_file)
        log(f"[INFO] Full classes: {len(classes)}  (timestamp {input_ts})")
    except Exception as exc:
        log(f"[ERROR] Could not load input: {exc}")
        append_to_batch_log(f"ERROR: momence_class_customers_full_api.py — {exc}")
        sys.exit(1)

    if not classes:
        log("[WARN] No classes in input file. Exiting.")
        append_to_batch_log("momence_class_customers_full_api.py: no full classes found, exiting")
        sys.exit(0)

    # Authenticate
    try:
        client = MomenceAPIClient()
        client.authenticate()
    except Exception as exc:
        log(f"[ERROR] Auth failed: {exc}")
        append_to_batch_log(f"ERROR: momence_class_customers_full_api.py auth — {exc}")
        sys.exit(1)

    # Fetch bookings
    all_rows:   list = []
    failed_ids: list = []

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

    summary = (f"momence_class_customers_full_api.py complete: "
               f"{len(classes)} full classes, {len(all_rows)} customer rows, "
               f"{len(failed_ids)} failures")
    log(f"\n[SUMMARY] {summary}")
    if failed_ids:
        log(f"[WARN] Failed class IDs: {', '.join(failed_ids)}")
    append_to_batch_log(summary)

    sys.exit(1 if failed_ids else 0)


if __name__ == "__main__":
    main()
