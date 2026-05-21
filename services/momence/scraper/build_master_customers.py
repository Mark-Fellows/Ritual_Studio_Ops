"""
build_master_customers.py
=========================
Build / refresh master_customers.csv from local Momence exports — pure data
merge, no Selenium, runs in seconds.

Why this exists
---------------
The dashboard popup (per-class drill-through) needs a real member name, not
just an email. None of the booking exports include first/last name; the only
Momence export that does is the "Customer list" report. Mark already
downloaded that once on 22 Oct 2025 (momence-customer-list-report 2025 10 22.csv,
29,122 customers).

Strategy
--------
1. Bootstrap (run once, automatic): if master_customers.csv does not yet exist,
   seed it from the most recent momence-customer-list-report YYYY MM DD.csv.
2. Daily refresh (runs every chain run): merge in any new email addresses
   that appear in:
     - Momence-No-Card-Customers.csv      (new sign-ups without a card)
     - master_non_member_customers.csv    (new visitors who aren't members)
     - master_membership_sales_summary.csv (new paying members)
   Dedupe by lower-cased email; keep the most-complete name (longest
   first+last); preserve existing phone numbers.

Output
------
master_customers.csv with columns:
    First Name, Last Name, Email, Phone, Source, Last Updated

Usage
-----
    python build_master_customers.py            # daily incremental (default)
    python build_master_customers.py --rebuild  # discard master, rebuild from scratch

Idempotent — safe to re-run.
"""

import os
import sys
import glob
import csv
import datetime
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_FILE = os.path.join(SCRIPT_DIR, "master_customers.csv")
# Master batch log — moved out of OneDrive on 2026-05-18 to stop sync locks
# truncating writes. Falls back to the legacy in-tree path if the local
# folder is absent (e.g. clean checkout on a new machine).
_LOCAL_BATCH_LOG_DIR = r"C:\Users\markj\Momence_local_logs"
if os.path.isdir(_LOCAL_BATCH_LOG_DIR):
    BATCH_LOG = os.path.join(_LOCAL_BATCH_LOG_DIR, "Momence_batch_log.txt")
else:
    BATCH_LOG = os.path.join(SCRIPT_DIR, "Log_files", "Momence_batch_log.txt")

MASTER_HEADERS = ["First Name", "Last Name", "Email", "Phone", "Source", "Last Updated"]


# ----------------------------------------------------------------------------
# Logging helper (matches the pattern used by every other script in the chain)
# ----------------------------------------------------------------------------
def append_to_batch_log(message: str) -> None:
    """Append a timestamped line to Momence_batch_log.txt (best effort)."""
    import time
    line = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"
    try:
        os.makedirs(os.path.dirname(BATCH_LOG), exist_ok=True)
    except Exception:
        pass
    for attempt in range(3):
        try:
            with open(BATCH_LOG, "a", encoding="utf-8") as bf:
                bf.write(line)
            return
        except Exception:
            time.sleep(1)
    print(f"[BATCH LOG WRITE FAILED] {line.rstrip()}", file=sys.stderr)


# ----------------------------------------------------------------------------
# Email normalisation — single source of truth for dedupe key
# ----------------------------------------------------------------------------
def normalise_email(raw: str) -> str:
    if not raw:
        return ""
    return raw.strip().lower()


# ----------------------------------------------------------------------------
# Name helpers
# ----------------------------------------------------------------------------
def _split_full_name(full: str):
    """Split 'First Last' into ('First', 'Last'). Last name may be empty."""
    if not full:
        return ("", "")
    parts = full.strip().split(maxsplit=1)
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])


def _name_score(first: str, last: str) -> int:
    """How 'complete' is a name? Used to pick the best of competing entries."""
    return (1 if first.strip() else 0) + (1 if last.strip() else 0) + len((first + last).strip())

# ----------------------------------------------------------------------------
# Source readers — each yields dicts with keys: first, last, email, phone, source
# ----------------------------------------------------------------------------
def _read_csv_safe(path):
    """Read a CSV with tolerant decoding. Returns (headers, rows) or ([], [])."""
    if not os.path.exists(path):
        return [], []
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            rd = csv.DictReader(f)
            return rd.fieldnames or [], list(rd)
    except Exception as exc:
        print(f"[WARN] Could not read {os.path.basename(path)}: {exc}", file=sys.stderr)
        return [], []


def read_bootstrap_export(script_dir):
    """Read the most recent momence-customer-list-report YYYY MM DD.csv.

    Returns a list of {first, last, email, phone, source} dicts.
    """
    matches = sorted(glob.glob(os.path.join(script_dir, "momence-customer-list-report*.csv")))
    if not matches:
        return [], None
    latest = matches[-1]
    headers, rows = _read_csv_safe(latest)
    out = []
    for r in rows:
        email = normalise_email(r.get("Customer Email") or r.get("Email") or "")
        if not email:
            continue
        out.append({
            "first": (r.get("Customer first name") or r.get("First Name") or "").strip(),
            "last":  (r.get("Customer last name")  or r.get("Last Name")  or "").strip(),
            "email": email,
            "phone": (r.get("Phone number") or r.get("Phone Number") or r.get("Phone") or "").strip(),
            "source": "bootstrap_export",
        })
    return out, latest


def read_no_card_customers(script_dir):
    """Read Momence-No-Card-Customers.csv (current snapshot of card-less customers)."""
    p = os.path.join(script_dir, "Momence-No-Card-Customers.csv")
    headers, rows = _read_csv_safe(p)
    out = []
    for r in rows:
        email = normalise_email(r.get("Email") or "")
        if not email:
            continue
        out.append({
            "first": (r.get("First Name") or "").strip(),
            "last":  (r.get("Last Name")  or "").strip(),
            "email": email,
            "phone": (r.get("Phone Number") or "").strip(),
            "source": "no_card_customers",
        })
    return out


def read_non_member_customers(script_dir):
    """Read master_non_member_customers.csv. Splits 'Customer Name' into first/last."""
    p = os.path.join(script_dir, "master_non_member_customers.csv")
    headers, rows = _read_csv_safe(p)
    out = []
    for r in rows:
        email = normalise_email(r.get("Customer Email") or "")
        if not email:
            continue
        first, last = _split_full_name(r.get("Customer Name") or "")
        out.append({
            "first": first, "last": last, "email": email,
            "phone": "", "source": "non_member_customers",
        })
    return out


def read_membership_sales(script_dir):
    """Read master_membership_sales_summary.csv — captures new paying members.

    The actual column names vary; we look for any 'email'-ish column and any
    'name' column.
    """
    p = os.path.join(script_dir, "master_membership_sales_summary.csv")
    if not os.path.exists(p):
        return []
    # Read headers first to find the right columns (cheaper than full DictReader on 11MB)
    with open(p, "r", encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f)
        headers = next(rd, [])
        if not headers:
            return []
        email_col = next((h for h in headers if "email" in h.lower()), None)
        name_col  = next((h for h in headers if "name"  in h.lower() and "host" not in h.lower()), None)
        if not email_col:
            return []
        email_idx = headers.index(email_col)
        name_idx  = headers.index(name_col) if name_col else -1
        out = []
        for r in rd:
            if len(r) <= email_idx:
                continue
            email = normalise_email(r[email_idx])
            if not email:
                continue
            full_name = r[name_idx] if name_idx >= 0 and len(r) > name_idx else ""
            first, last = _split_full_name(full_name)
            out.append({
                "first": first, "last": last, "email": email,
                "phone": "", "source": "membership_sales",
            })
    return out


# ----------------------------------------------------------------------------
# Existing master loader
# ----------------------------------------------------------------------------
def read_master(path):
    if not os.path.exists(path):
        return {}
    headers, rows = _read_csv_safe(path)
    out = {}
    for r in rows:
        email = normalise_email(r.get("Email") or "")
        if not email:
            continue
        out[email] = {
            "first":  (r.get("First Name") or "").strip(),
            "last":   (r.get("Last Name")  or "").strip(),
            "email":  email,
            "phone":  (r.get("Phone") or "").strip(),
            "source": (r.get("Source") or "").strip() or "existing",
        }
    return out


# ----------------------------------------------------------------------------
# Merge logic
# ----------------------------------------------------------------------------
def merge_record(existing, incoming):
    """Merge incoming into existing, keeping the most-complete name and any phone."""
    if not existing:
        return dict(incoming)
    out = dict(existing)
    # Pick the better name
    if _name_score(incoming["first"], incoming["last"]) > _name_score(out["first"], out["last"]):
        out["first"] = incoming["first"]
        out["last"]  = incoming["last"]
    # Prefer non-empty phone
    if incoming.get("phone") and not out.get("phone"):
        out["phone"] = incoming["phone"]
    # Keep original source if already known; else set incoming
    if not out.get("source"):
        out["source"] = incoming["source"]
    return out


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Build/refresh master_customers.csv")
    parser.add_argument("--rebuild", action="store_true",
                        help="Discard existing master and rebuild from scratch.")
    args = parser.parse_args()

    # Load existing master (or empty dict on --rebuild / first run)
    if args.rebuild:
        master = {}
        print("[INFO] --rebuild: starting from empty master.")
    else:
        master = read_master(MASTER_FILE)
        print(f"[INFO] Existing master_customers.csv: {len(master):,} rows.")

    bootstrap_used = None
    # If master is empty, seed from the bootstrap export
    if not master:
        boot, src = read_bootstrap_export(SCRIPT_DIR)
        if boot:
            print(f"[INFO] Bootstrapping from {os.path.basename(src)}: {len(boot):,} rows.")
            for rec in boot:
                if rec["email"] in master:
                    master[rec["email"]] = merge_record(master[rec["email"]], rec)
                else:
                    master[rec["email"]] = rec
            bootstrap_used = src
        else:
            print("[WARN] No master and no bootstrap CSV found.  Will build from daily sources only.")

    # Daily incremental — merge in current snapshots
    incremental_sources = [
        ("no_card_customers",     read_no_card_customers(SCRIPT_DIR)),
        ("non_member_customers",  read_non_member_customers(SCRIPT_DIR)),
        ("membership_sales",      read_membership_sales(SCRIPT_DIR)),
    ]
    added = 0
    updated = 0
    seen_in_run = 0
    for source_name, recs in incremental_sources:
        before_keys = set(master.keys())
        for rec in recs:
            seen_in_run += 1
            existing = master.get(rec["email"])
            merged = merge_record(existing, rec)
            master[rec["email"]] = merged
            if rec["email"] not in before_keys:
                added += 1
            elif existing != merged:
                updated += 1
        print(f"[INFO] Source '{source_name}': {len(recs):,} rows scanned.")

    # Write master atomically
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tmp = MASTER_FILE + ".tmp"
    rows_out = sorted(master.values(), key=lambda r: r["email"])
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=MASTER_HEADERS)
        wr.writeheader()
        for r in rows_out:
            wr.writerow({
                "First Name":   r["first"],
                "Last Name":    r["last"],
                "Email":        r["email"],
                "Phone":        r["phone"],
                "Source":       r["source"],
                "Last Updated": timestamp,
            })
    os.replace(tmp, MASTER_FILE)

    msg = (f"build_master_customers.py: {len(rows_out):,} customers "
           f"(+{added} new, {updated} updated)")
    if bootstrap_used:
        msg += f" — bootstrapped from {os.path.basename(bootstrap_used)}"
    print(f"[OK] {msg}")
    print(f"[OK] Written: {MASTER_FILE}")
    append_to_batch_log(msg)


if __name__ == "__main__":
    main()
