# -*- coding: utf-8 -*-
"""reconcile.py -- RSO Phase 5 daily reconciliation script.

Runs daily during the two-week parallel-run period (Phase 5).
Checks for data drift and unexpected legacy-app writes.

Usage:
    python scripts/reconcile.py [--days N] [--no-save]

Checks:
    1. Audit log origin split: [RSO] vs non-[RSO] entries in the last N days
    2. Cover requests by status: today vs yesterday snapshot
    3. Trainee bookings: pending count drift
    4. Teacher record count: unexpected deletions
    5. P1 flags: any condition that indicates legacy-app writes are still happening

Outputs:
    - Plain-text report to stdout
    - Report file saved to scripts/reconcile_reports/YYYY-MM-DD.txt
    - reconcile_state.json updated with today's snapshot

Exit codes:
    0  All clear (or warnings only)
    1  P1 issue detected (unexpected legacy writes or critical drift)
    2  Configuration error (Supabase unreachable)
"""
import sys
import json
import argparse
import datetime
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE     = Path(__file__).parent
_RSO_ROOT = _HERE.parent
_COVER    = _RSO_ROOT / "services" / "cover"
sys.path.insert(0, str(_COVER))

try:
    from config import SUPABASE_URL, SUPABASE_KEY, sb_get
except ImportError as e:
    print(f"ERROR: Cannot import config from {_COVER}: {e}")
    print("Ensure services/cover/config.py exists and .env is populated.")
    sys.exit(2)

# ── Constants ─────────────────────────────────────────────────────────────────
STATE_FILE   = _HERE / "reconcile_state.json"
REPORTS_DIR  = _HERE / "reconcile_reports"
REPORTS_DIR.mkdir(exist_ok=True)

RSO_MARKER   = "[RSO]"
P1_ISSUES    = []
WARNINGS     = []
REPORT_LINES = []


# ── Helpers ───────────────────────────────────────────────────────────────────
def log(line=""):
    REPORT_LINES.append(line)
    print(line)

def p1(msg):
    P1_ISSUES.append(msg)
    log(f"  [P1] {msg}")

def warn(msg):
    WARNINGS.append(msg)
    log(f"  [WARN] {msg}")

def ok(msg):
    log(f"  [OK] {msg}")

def safe_get(path, default=None):
    try:
        return sb_get(path)
    except Exception as e:
        warn(f"Query failed ({path}): {e}")
        return default


# ── Check 1: Audit log origin split ──────────────────────────────────────────
def check_audit_log(since_iso: str):
    log("\n-- Check 1: Audit log origin (last 24h) --")
    rows = safe_get(
        f"audit_log?created_at=gte.{since_iso}&select=description&limit=1000",
        default=[]
    )
    if rows is None:
        warn("Audit log query returned None — Supabase may be unreachable")
        return {}

    rso_count    = sum(1 for r in rows if r.get("description","").startswith(RSO_MARKER))
    legacy_count = len(rows) - rso_count

    log(f"  Total audit entries (last 24h): {len(rows)}")
    log(f"  RSO writes ([RSO] prefix):      {rso_count}")
    log(f"  Non-RSO writes (legacy/other):  {legacy_count}")

    if legacy_count > 0:
        p1(f"{legacy_count} non-RSO audit entries found — legacy app is still making writes. "
           f"Investigate immediately.")
    else:
        ok("All audit entries originate from RSO.")

    return {"total": len(rows), "rso": rso_count, "legacy": legacy_count}


# ── Check 2: Cover requests by status ────────────────────────────────────────
def check_cover_requests():
    log("\n-- Check 2: Cover requests by status --")
    rows = safe_get("cover_requests?select=status&limit=2000", default=[])
    if rows is None:
        warn("cover_requests query failed")
        return {}

    counts = {}
    for r in rows:
        s = r.get("status", "unknown") or "unknown"
        counts[s] = counts.get(s, 0) + 1

    log(f"  Total cover requests: {sum(counts.values())}")
    for status, n in sorted(counts.items()):
        log(f"    {status}: {n}")

    return counts


# ── Check 3: Trainee bookings by status ──────────────────────────────────────
def check_trainee_bookings():
    log("\n-- Check 3: Trainee bookings by status --")
    rows = safe_get("trainee_bookings?select=status&limit=2000", default=[])
    if rows is None:
        warn("trainee_bookings query failed")
        return {}

    counts = {}
    for r in rows:
        s = r.get("status", "unknown") or "unknown"
        counts[s] = counts.get(s, 0) + 1

    log(f"  Total trainee bookings: {sum(counts.values())}")
    for status, n in sorted(counts.items()):
        log(f"    {status}: {n}")

    return counts


# ── Check 4: Teacher count integrity ─────────────────────────────────────────
def check_teachers():
    log("\n-- Check 4: Teacher records --")
    rows = safe_get("teachers?select=id&limit=500", default=[])
    if rows is None:
        warn("teachers query failed")
        return {}

    count = len(rows)
    log(f"  Total teacher records: {count}")
    return {"count": count}


# ── Drift comparison against yesterday's snapshot ────────────────────────────
def compare_snapshot(today: dict, yesterday: dict):
    log("\n-- Drift comparison vs yesterday --")
    if not yesterday:
        log("  No previous snapshot found — this run establishes the baseline.")
        return

    # Teacher count drift
    t_today = today.get("teachers", {}).get("count", 0)
    t_yest  = yesterday.get("teachers", {}).get("count", 0)
    if t_today < t_yest:
        p1(f"Teacher count dropped from {t_yest} to {t_today}. "
           f"Check for unexpected deletions.")
    elif t_today > t_yest:
        ok(f"Teacher count increased {t_yest} → {t_today} (new teachers added).")
    else:
        ok(f"Teacher count unchanged: {t_today}.")

    # Cover requests total drift
    cr_today = sum(today.get("cover_requests", {}).values())
    cr_yest  = sum(yesterday.get("cover_requests", {}).values())
    if cr_today < cr_yest:
        p1(f"Cover request count dropped {cr_yest} → {cr_today}. "
           f"Records may have been deleted.")
    elif cr_today > cr_yest:
        ok(f"Cover requests increased {cr_yest} → {cr_today} (new requests received).")
    else:
        ok(f"Cover request count unchanged: {cr_today}.")

    # Trainee bookings pending drift
    tb_pend_today = today.get("trainee_bookings", {}).get("pending", 0)
    tb_pend_yest  = yesterday.get("trainee_bookings", {}).get("pending", 0)
    if tb_pend_today > tb_pend_yest + 20:
        warn(f"Pending trainee bookings grew by {tb_pend_today - tb_pend_yest} in 24h. "
             f"May indicate a processing backlog.")
    else:
        ok(f"Pending trainee bookings: {tb_pend_today} (was {tb_pend_yest}).")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="RSO Phase 5 reconciliation script")
    parser.add_argument("--days", type=int, default=1,
                        help="Lookback window in days (default: 1)")
    parser.add_argument("--no-save", action="store_true",
                        help="Do not save snapshot or report file")
    args = parser.parse_args()

    run_date = datetime.date.today().isoformat()
    since_dt = datetime.datetime.utcnow() - datetime.timedelta(days=args.days)
    since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    log(f"RSO Phase 5 Reconciliation Report — {run_date}")
    log(f"Lookback window: {args.days} day(s) (since {since_iso} UTC)")
    log(f"Supabase project: {SUPABASE_URL}")
    log("=" * 60)

    # Load yesterday's snapshot
    yesterday = {}
    if STATE_FILE.exists():
        try:
            yesterday = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            warn("Could not parse reconcile_state.json — treating as first run.")

    # Run checks
    audit   = check_audit_log(since_iso)
    cover   = check_cover_requests()
    trainee = check_trainee_bookings()
    teach   = check_teachers()

    # Build today's snapshot
    today_state = {
        "date":             run_date,
        "audit_24h":        audit,
        "cover_requests":   cover,
        "trainee_bookings": trainee,
        "teachers":         teach,
    }

    # Drift comparison
    compare_snapshot(today_state, yesterday)

    # Summary
    log("\n" + "=" * 60)
    log(f"P1 issues: {len(P1_ISSUES)}")
    log(f"Warnings:  {len(WARNINGS)}")
    if P1_ISSUES:
        log("\nP1 ISSUES — ACTION REQUIRED:")
        for i, msg in enumerate(P1_ISSUES, 1):
            log(f"  {i}. {msg}")
    if WARNINGS:
        log("\nWarnings (investigate if recurring):")
        for msg in WARNINGS:
            log(f"  - {msg}")

    if not P1_ISSUES and not WARNINGS:
        log("\nAll checks passed. Parallel run is GREEN.")
    elif not P1_ISSUES:
        log("\nNo P1 issues. Parallel run is GREEN with warnings.")
    else:
        log("\nP1 ISSUES DETECTED. Parallel run is RED — investigate immediately.")

    # Save snapshot and report
    if not args.no_save:
        STATE_FILE.write_text(json.dumps(today_state, indent=2), encoding="utf-8")
        report_path = REPORTS_DIR / f"{run_date}.txt"
        report_path.write_text("\n".join(REPORT_LINES), encoding="utf-8")
        log(f"\nReport saved: {report_path}")
        log(f"Snapshot updated: {STATE_FILE}")

    sys.exit(1 if P1_ISSUES else 0)


if __name__ == "__main__":
    main()
