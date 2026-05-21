"""
enrich_resolved_classes_from_momence.py — Stage 3 follow-up.

For every cover_request that has resolved_classes populated, calls the
Momence per-session detail endpoint
    GET /api/v2/host/sessions/{sessionId}
once per resolved Class Number and stamps the following fields into
the snapshot:

    teacher                 — currently assigned teacher (or TBA / null)
    original_teacher        — who normally teaches this slot
    additional_teachers     — co-teacher list (names)
    is_cancelled            — surface in dashboard
    is_draft                — same
    booking_count           — live booked count (refreshed each run)
    waitlist_booking_count  — live waitlist count (refreshed each run)

Per-ID is preferred over the bulk /sessions list endpoint because the
detail response carries originalTeacher, additionalTeachers, isCancelled
and isDraft — all useful for cover-management UI. The bulk endpoint only
returns the current teacher.

Usage
-----
    python stage3/enrich_resolved_classes_from_momence.py             # DRY RUN
    python stage3/enrich_resolved_classes_from_momence.py --apply
    python stage3/enrich_resolved_classes_from_momence.py --limit 5
    python stage3/enrich_resolved_classes_from_momence.py --overwrite

Idempotent. By default `original_teacher` is only filled when blank
(it is a stable historical fact); all other fields - including the live
`teacher` assignment - always refresh from Momence so the dashboard
reflects current cover-teacher changes within an hour. --overwrite
additionally re-stamps `original_teacher` regardless of current value.

Changed 2026-05-18: `teacher` was previously skipped when non-blank,
which froze the dashboard's teacher display on whatever value Momence
returned at first resolution. For cover management we want the live
value, so `teacher` is now treated like booking_count / is_cancelled
and always refreshed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Force UTF-8, line-buffered stdout. Without this, output is
# block-buffered when stdout is a pipe (cmd /c, scheduled task), which
# meant the per-row progress lines and the final summary used to land
# in the log out of order - leading to misleading "rows_updated=0"
# summaries while the script was actually mid-run. The hourly runner
# in run_monitor.bat already sets PYTHONIOENCODING=utf-8 but this is
# defence-in-depth for manual invocations.
try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import our project's config (Supabase helpers) BEFORE we extend sys.path
# with the Momence client path - otherwise the Momence project's own
# config.py would shadow ours and the import of sb_get/sb_patch fails.
from config import sb_get, sb_patch

# Momence API client lives in a separate project. Append (not insert) so
# our project_root keeps priority for any other module name clashes.
# RSO Phase 3: config.py (imported above) sets services/momence/ on sys.path
from momence_api_client import MomenceAPIClient  # noqa: E402 (path set by config)


_SESSION_DETAIL_PATH = "/api/v2/host/sessions/{session_id}"
_BLANK_TEACHER_VALUES = {None, "", "NA", "TBA", "tba", "n/a", "N/A"}


def get_session_detail(client, session_id):
    """Try client.get_session() then fall back to direct HTTP."""
    if hasattr(client, "get_session") and callable(client.get_session):
        try:
            return client.get_session(session_id)
        except Exception as e:
            print(f"    [api] get_session({session_id}) raised "
                  f"{type(e).__name__}: {e}")
            return None

    import requests
    base = (getattr(client, "BASE_URL", None) or "https://api.momence.com").rstrip("/")
    url = f"{base}{_SESSION_DETAIL_PATH.format(session_id=session_id)}"

    sess = getattr(client, "session", None) or getattr(client, "_session", None)
    if sess is not None and hasattr(sess, "get"):
        try:
            r = sess.get(url, timeout=15)
        except Exception as e:
            print(f"    [api] HTTP via client.session failed: {e}")
            return None
    else:
        token = (getattr(client, "access_token", None)
                 or getattr(client, "_access_token", None)
                 or getattr(client, "token", None))
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
        except Exception as e:
            print(f"    [api] HTTP GET failed: {e}")
            return None

    if r.status_code == 404:
        return None
    if r.status_code == 401 and hasattr(client, "authenticate"):
        try:
            client.authenticate()
        except Exception:
            pass
        new_token = (getattr(client, "access_token", None)
                     or getattr(client, "_access_token", None)
                     or getattr(client, "token", None))
        if new_token:
            headers = {"Accept": "application/json",
                       "Authorization": f"Bearer {new_token}"}
            try:
                r = requests.get(url, headers=headers, timeout=15)
            except Exception:
                return None
    if not r.ok:
        print(f"    [api] HTTP {r.status_code} for session {session_id}: "
              f"{r.text[:140]}")
        return None
    try:
        return r.json()
    except Exception as e:
        print(f"    [api] cannot parse JSON for session {session_id}: {e}")
        return None


def _name_from_teacher_obj(t):
    if isinstance(t, str):
        s = t.strip()
        return s or None
    if isinstance(t, dict):
        for k in ("name", "displayName"):
            v = t.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        first = t.get("firstName") or ""
        last = t.get("lastName") or ""
        if isinstance(first, str) or isinstance(last, str):
            full = ((str(first) if first else "") + " "
                    + (str(last) if last else "")).strip()
            return full or None
    return None


def extract_fields(detail):
    if not isinstance(detail, dict):
        return {}
    additionals = []
    raw_additionals = detail.get("additionalTeachers")
    if isinstance(raw_additionals, list):
        for at in raw_additionals:
            nm = _name_from_teacher_obj(at)
            if nm and nm not in additionals:
                additionals.append(nm)
    bc = detail.get("bookingCount")
    wbc = detail.get("waitlistBookingCount")
    return {
        "teacher": _name_from_teacher_obj(detail.get("teacher")),
        "original_teacher": _name_from_teacher_obj(detail.get("originalTeacher")),
        "additional_teachers": additionals or None,
        "is_cancelled": bool(detail.get("isCancelled")),
        "is_draft": bool(detail.get("isDraft")),
        "booking_count": int(bc) if isinstance(bc, (int, float)) else None,
        "waitlist_booking_count": int(wbc) if isinstance(wbc, (int, float)) else None,
    }


def fetch_rows():
    return sb_get(
        "cover_requests",
        params={
            "select": "cover_request_id,requesting_teacher_name_raw,"
                      "resolved_classes,classes_resolved_at,status",
            "resolved_classes": "not.is.null",
            "order": "message_timestamp.asc",
        },
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Write changes back to Supabase (default: dry run).")
    ap.add_argument("--limit", type=int, default=None,
                    help="Only process the first N rows.")
    ap.add_argument("--overwrite", action="store_true",
                    help="Re-stamp teacher even when snapshot already has a "
                         "non-blank value.")
    args = ap.parse_args()

    print("=== enrich_resolved_classes_from_momence (per-ID detail) ===")
    print(f"Mode      : {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Overwrite : {args.overwrite}")
    print(f"Limit     : {args.limit or 'all'}")
    print()

    rows = fetch_rows()
    if args.limit is not None:
        rows = rows[: args.limit]
    print(f"Found {len(rows)} cover_request(s) with resolved_classes set.\n")
    if not rows:
        return 0

    print("Authenticating with Momence API...")
    client = MomenceAPIClient()
    client.authenticate()
    print("OK.\n")

    # Cache so overlapping session_ids are only fetched once across rows
    detail_cache = {}

    counts = {
        "rows_with_changes": 0,    # rows where at least one field differed
        "fields_updated": 0,       # total per-key changes across all rows
        "rows_unchanged": 0,       # rows where every field already matched
        "patches_succeeded": 0,    # successful Supabase PATCH calls
        "patches_failed": 0,       # PATCH calls that raised
        "api_404": 0,              # Momence session detail not found
    }

    for i, r in enumerate(rows, 1):
        rid = r["cover_request_id"]
        teacher_name = r.get("requesting_teacher_name_raw") or "?"
        rc = r.get("resolved_classes") or []
        if not isinstance(rc, list) or not rc:
            continue

        per_row_changes = 0
        for c in rc:
            sid = c.get("momence_session_id")
            if not isinstance(sid, int):
                continue
            if sid in detail_cache:
                fields = detail_cache[sid]
            else:
                detail = get_session_detail(client, sid)
                if detail is None:
                    counts["api_404"] += 1
                    detail_cache[sid] = {}
                    continue
                fields = extract_fields(detail)
                detail_cache[sid] = fields

            for key, new_val in fields.items():
                cur = c.get(key)
                # Never blank a known value with null/None (any field).
                if new_val is None and cur is not None:
                    continue
                # original_teacher is a stable historical fact - only fill
                # blanks unless --overwrite is explicitly requested.
                if not args.overwrite and key == "original_teacher":
                    if cur not in _BLANK_TEACHER_VALUES:
                        continue
                # `teacher` always refreshes (live current assignment - may
                # change as cover teachers are confirmed/changed in Momence),
                # as do booking_count / waitlist_booking_count (they change
                # throughout the day), is_cancelled, is_draft and
                # additional_teachers.
                if cur != new_val:
                    c[key] = new_val
                    per_row_changes += 1

        # Heartbeat every 10 rows so long-running invocations show progress
        # in the log even when nothing has changed. Always emits regardless
        # of whether the row was updated.
        if i % 10 == 0:
            print(f"   [heartbeat] processed {i}/{len(rows)} rows "
                  f"(with_changes={counts['rows_with_changes']} "
                  f"unchanged={counts['rows_unchanged']})")

        if per_row_changes == 0:
            counts["rows_unchanged"] += 1
            continue

        counts["rows_with_changes"] += 1
        counts["fields_updated"] += per_row_changes

        sample = next((c for c in rc if c.get("teacher") not in _BLANK_TEACHER_VALUES), None)
        if sample:
            extra = ""
            if sample.get("original_teacher"):
                extra = f" (orig: {sample.get('original_teacher')})"
            sample_str = (f"e.g. session {sample.get('momence_session_id')} on "
                          f"{sample.get('date')} -> teacher='{sample.get('teacher')}'"
                          + extra)
        else:
            sample_str = "(no non-blank teacher samples)"

        print(f"[{i}/{len(rows)}] {rid[:8]}  ({teacher_name}) - "
              f"updated {per_row_changes} field(s) across {len(rc)} class(es)")
        print(f"   {sample_str}")

        if args.apply:
            try:
                sb_patch(
                    "cover_requests",
                    {"resolved_classes": rc},
                    match_params={"cover_request_id": f"eq.{rid}"},
                )
                counts["patches_succeeded"] += 1
                print("   UPDATED")
            except Exception as e:
                counts["patches_failed"] += 1
                print(f"   [FAIL] PATCH: {e}")
        else:
            print("   [DRY RUN] would PATCH resolved_classes")

    print()
    print("=" * 60)
    fetched = sum(1 for v in detail_cache.values() if v)
    # Two numbers worth cross-checking:
    #   rows_with_changes : rows where at least one field differed from
    #                       Momence. Should equal patches_succeeded in
    #                       --apply mode if every PATCH worked.
    #   fields_updated    : total per-key changes (a row that updates
    #                       teacher AND booking_count on 2 classes
    #                       contributes 4).
    mode_word = "APPLY" if args.apply else "DRY RUN"
    print(f"Done ({mode_word}).")
    print(f"  rows_processed       = {len(rows)}")
    print(f"  rows_with_changes    = {counts['rows_with_changes']}")
    print(f"  rows_unchanged       = {counts['rows_unchanged']}")
    print(f"  fields_updated       = {counts['fields_updated']}")
    if args.apply:
        print(f"  patches_succeeded    = {counts['patches_succeeded']}")
        print(f"  patches_failed       = {counts['patches_failed']}")
    print(f"  unique_sessions_seen = {fetched}")
    print(f"  api_404              = {counts['api_404']}")
    if not args.apply:
        print("\nDRY RUN - re-run with --apply to update Supabase.")
    return 0 if counts["patches_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
