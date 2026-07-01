# -*- coding: utf-8 -*-
"""reconcile.py -- RSO daily reconciliation script.

Checks for data drift and unexpected legacy-app writes across the shared DB.

Usage:
    python scripts/reconcile.py [--days N] [--no-save]

Checks:
    1. Audit log origin split: [RSO] vs non-[RSO] entries in the last N days
    2. Cover requests by status: today vs yesterday snapshot
    3. Trainee bookings: pending count drift
    4. Teacher record count: unexpected deletions
    5. Drift comparison vs yesterday's snapshot

Outputs:
    - Plain-text report to stdout + scripts/reconcile_reports/YYYY-MM-DD.txt
    - reconcile_state.json updated with today's snapshot (ONLY on a trustworthy run)

Exit codes:
    0  All clear (or warnings only)
    1  P1 issue OR a hard FAILURE (query error / implausible zero-read) — alert sent
    2  Configuration error (Supabase unreachable, or NOT running with the service-role key)

P0-8 hardening (2026-06-30): reads now use the SERVICE_ROLE key (RLS is enabled on the
shared tables, so the anon key would hide rows and report false-GREEN); query errors and
implausible zero-reads are hard failures; a failed run does not overwrite the baseline
snapshot; and any failure exits non-zero and fires an alert (webhook and/or email).
"""
import os
import sys
import json
import base64
import argparse
import datetime
import requests
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE     = Path(__file__).parent
_RSO_ROOT = _HERE.parent
_COVER    = _RSO_ROOT / "services" / "cover"
sys.path.insert(0, str(_COVER))

try:
    from config import (
        SUPABASE_URL, SUPABASE_KEY, sb_get,
        SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, NOTIFY_FROM,
    )
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
FAILURES     = []          # hard failures (query errors / implausible zeros) → exit 1 + alert
REPORT_LINES = []

# Absolute-zero floors: a count below these is implausible and treated as a FAILURE,
# so a blocked/failed read can never masquerade as a healthy "0 → GREEN".
MIN_TEACHERS       = int(os.getenv("RECON_MIN_TEACHERS", "1"))
MIN_COVER_REQUESTS = int(os.getenv("RECON_MIN_COVER_REQUESTS", "1"))


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

def fail(msg):
    FAILURES.append(msg)
    log(f"  [FAIL] {msg}")

def ok(msg):
    log(f"  [OK] {msg}")


def _jwt_role(token: str):
    """Best-effort decode of a Supabase JWT's `role` claim (no signature check)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)              # pad base64
        return json.loads(base64.urlsafe_b64decode(payload)).get("role")
    except Exception:
        return None


def require_service_role():
    """Abort unless queries will use the SERVICE_ROLE key. With RLS enabled on the shared
    tables, the anon key silently returns RLS-filtered (often empty) rows and reports a
    false-GREEN reconciliation."""
    key  = os.getenv("SUPABASE_SERVICE_KEY") or SUPABASE_KEY
    role = _jwt_role(key)
    if role != "service_role":
        print(f"ERROR: reconcile must run with the SERVICE_ROLE key (found role={role!r}).")
        print("RLS is enabled on the shared tables, so the anon key would hide rows and")
        print("produce false-GREEN reconciliations. Set SUPABASE_SERVICE_KEY in the RSO .env.")
        sys.exit(2)


def send_alert(subject: str, body: str):
    """Best-effort failure alert — Teams/Slack webhook and/or SMTP email.
    Configure ALERT_WEBHOOK_URL and/or SMTP_USER + SMTP_PASSWORD (+ ALERT_EMAIL)."""
    sent = []
    webhook = os.getenv("ALERT_WEBHOOK_URL")
    if webhook:
        try:
            requests.post(webhook, json={"text": f"**{subject}**\n\n{body[:3500]}"}, timeout=15)
            sent.append("webhook")
        except Exception as e:
            print(f"[alert] webhook failed: {e}")
    recipient = os.getenv("ALERT_EMAIL") or SMTP_USER
    if SMTP_USER and SMTP_PASSWORD and recipient:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"]    = NOTIFY_FROM
            msg["To"]      = recipient
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
                s.starttls()
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
            sent.append(f"email:{recipient}")
        except Exception as e:
            print(f"[alert] email failed: {e}")
    print(f"[alert] sent via {', '.join(sent)}" if sent
          else "[alert] NO channel configured — set ALERT_WEBHOOK_URL or SMTP_USER/PASSWORD (+ ALERT_EMAIL).")


def safe_get(path, default=None):
    """GET via the SERVICE_ROLE key (bypasses RLS). On error, records a hard FAILURE and
    returns None so callers can distinguish None (failed) from [] (genuinely empty)."""
    try:
        return sb_get(path, service_key=True)
    except Exception as e:
        fail(f"Query failed ({path}): {e}")
        return None


# ── Check 1: Audit log origin split ──────────────────────────────────────────
def check_audit_log(since_iso: str):
    log("\n-- Check 1: Audit log origin (last 24h) --")
    rows = safe_get(
        f"audit_log?created_at=gte.{since_iso}&select=description&limit=1000",
        default=[]
    )
    if rows is None:
        return {}                       # query failed — already recorded as a FAILURE

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
        return {}                       # query failed — already recorded as a FAILURE

    counts = {}
    for r in rows:
        s = r.get("status", "unknown") or "unknown"
        counts[s] = counts.get(s, 0) + 1

    total = sum(counts.values())
    log(f"  Total cover requests: {total}")
    for status, n in sorted(counts.items()):
        log(f"    {status}: {n}")

    if total < MIN_COVER_REQUESTS:
        fail(f"Cover requests total is {total} (below floor {MIN_COVER_REQUESTS}) — implausible; "
             f"likely a blocked read, not a healthy zero.")
    return counts


# ── Check 3: Trainee bookings by status ──────────────────────────────────────
def check_trainee_bookings():
    log("\n-- Check 3: Trainee bookings by status --")
    rows = safe_get("trainee_bookings?select=status&limit=2000", default=[])
    if rows is None:
        return {}                       # query failed — already recorded as a FAILURE

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
        return {}                       # query failed — already recorded as a FAILURE

    count = len(rows)
    log(f"  Total teacher records: {count}")
    if count < MIN_TEACHERS:
        fail(f"Teacher count is {count} (below floor {MIN_TEACHERS}) — implausible; "
             f"likely a blocked read or data loss, not a healthy zero.")
    else:
        ok(f"Teacher count looks sane: {count}.")
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
    parser = argparse.ArgumentParser(description="RSO reconciliation script")
    parser.add_argument("--days", type=int, default=1,
                        help="Lookback window in days (default: 1)")
    parser.add_argument("--no-save", action="store_true",
                        help="Do not save snapshot or report file")
    args = parser.parse_args()

    run_date = datetime.date.today().isoformat()
    since_dt = datetime.datetime.utcnow() - datetime.timedelta(days=args.days)
    since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    log(f"RSO Reconciliation Report — {run_date}")
    log(f"Lookback window: {args.days} day(s) (since {since_iso} UTC)")
    log(f"Supabase project: {SUPABASE_URL}")
    log("=" * 60)

    # Reads must use the service-role key (RLS is enabled on the shared tables).
    require_service_role()

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
    log(f"Failures:  {len(FAILURES)}")
    log(f"P1 issues: {len(P1_ISSUES)}")
    log(f"Warnings:  {len(WARNINGS)}")
    if FAILURES:
        log("\nFAILURES — this run could not be trusted:")
        for i, msg in enumerate(FAILURES, 1):
            log(f"  {i}. {msg}")
    if P1_ISSUES:
        log("\nP1 ISSUES — ACTION REQUIRED:")
        for i, msg in enumerate(P1_ISSUES, 1):
            log(f"  {i}. {msg}")
    if WARNINGS:
        log("\nWarnings (investigate if recurring):")
        for msg in WARNINGS:
            log(f"  - {msg}")

    failed = bool(FAILURES) or bool(P1_ISSUES)
    if FAILURES:
        log("\nRECONCILE FAILED — read error or implausible zero. Result is NOT trustworthy.")
    elif P1_ISSUES:
        log("\nP1 ISSUES DETECTED. Parallel run is RED — investigate immediately.")
    elif WARNINGS:
        log("\nNo P1 issues. Parallel run is GREEN with warnings.")
    else:
        log("\nAll checks passed. Parallel run is GREEN.")

    # Save the report always; save the snapshot ONLY on a trustworthy run (a failed read
    # must not poison tomorrow's drift comparison by writing a bogus baseline).
    if not args.no_save:
        report_path = REPORTS_DIR / f"{run_date}.txt"
        report_path.write_text("\n".join(REPORT_LINES), encoding="utf-8")
        log(f"\nReport saved: {report_path}")
        if not failed:
            STATE_FILE.write_text(json.dumps(today_state, indent=2), encoding="utf-8")
            log(f"Snapshot updated: {STATE_FILE}")
        else:
            log("Snapshot NOT updated (run failed — keeping the last good baseline).")

    # Fail loud: alert + non-zero exit on any failure or P1.
    if failed:
        subject = f"[Ritual reconcile] {'FAILURE' if FAILURES else 'P1'} — {run_date}"
        send_alert(subject, "\n".join(REPORT_LINES))

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
