"""
backfill_resolved_classes.py -- Stage 3, one-shot backfill.

Re-resolves every existing cover_request that doesn't yet have
momence_session_ids set, using the (now multi-date capable) NLP parser
plus the resolve_classes module. Also repairs any records where
momence_session_ids was stored as a JSON *string* instead of a JSON
*array* due to a json.dumps() bug in cover_processor.py (fixed 2026-05-13).

Writes back:
    momence_session_ids   JSONB array of Momence Class Numbers
    resolved_classes      JSONB array of per-class snapshots
    classes_resolved_at   TIMESTAMPTZ

Usage
-----
    python stage3/backfill_resolved_classes.py             # DRY RUN (default)
    python stage3/backfill_resolved_classes.py --apply     # actually update
    python stage3/backfill_resolved_classes.py --limit 5   # only first N rows
    python stage3/backfill_resolved_classes.py --max-matches 5  # cap per row

Safety
------
- DRY RUN by default. Prints exactly what would change for every row.
- One PATCH per row, with the matched cover_request_id in the URL -- never
  mass-updates.
- Skips rows that already have momence_session_ids populated.
- Skips rows where the resolver returns more than --max-matches results
  (default 10) to avoid tagging context-only messages with every class
  on a given day.
- Re-parses the raw_message via the same Claude prompt the live monitor
  uses, so the result is consistent with going-forward behaviour.
- If parsing or resolution fails for a row, the row is left untouched and
  the failure is logged.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "stage2"))
sys.path.insert(0, str(PROJECT_ROOT / "stage3"))

from config import sb_get, sb_patch, MOMENCE_DATA_DIR
from datetime import date as _date, time as _time
from nlp_parser import NLPParser
from resolve_classes import (
    CoverRequestGroup,
    CoverRequestQuery,
    load_future_classes,
    resolve_request_to_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])  # tolerate timestamptz suffix
    except ValueError:
        return None


def fetch_unresolved_requests(limit: int | None = None) -> list[dict]:
    """Cover requests still missing momence_session_ids (or never resolved)."""
    params: dict[str, str] = {
        "select": (
            "cover_request_id,raw_message,requesting_teacher_name_raw,"
            "class_date,class_time,studio,discipline_code,"
            "message_timestamp,whatsapp_channel_id,status,"
            "momence_session_ids,classes_resolved_at"
        ),
        "or": "(momence_session_ids.is.null,classes_resolved_at.is.null)",
        "order": "message_timestamp.asc",
    }
    if limit is not None:
        params["limit"] = str(limit)
    return sb_get("cover_requests", params=params)


def fetch_string_encoded_requests(limit: int | None = None) -> list[dict]:
    """Return cover_requests where momence_session_ids was stored as a JSON
    *string* instead of a JSON *array* -- the encoding bug that existed in
    cover_processor.py before 2026-05-13.

    These rows have BOTH fields non-null so they are invisible to
    fetch_unresolved_requests, but the dashboard sees Array.isArray("...")
    == false and shows 'Not resolved against Momence yet'.

    Detection: Supabase returns JSONB strings as Python str and JSONB arrays
    as Python list, so isinstance(row["momence_session_ids"], str) is the
    reliable client-side test.
    """
    params: dict[str, str] = {
        "select": (
            "cover_request_id,raw_message,requesting_teacher_name_raw,"
            "class_date,class_time,studio,discipline_code,"
            "message_timestamp,whatsapp_channel_id,status,"
            "momence_session_ids,resolved_classes,classes_resolved_at"
        ),
        "momence_session_ids": "not.is.null",
        "classes_resolved_at": "not.is.null",
        "order": "message_timestamp.asc",
    }
    if limit is not None:
        params["limit"] = str(limit)
    all_rows = sb_get("cover_requests", params=params)
    return [
        r for r in all_rows
        if isinstance(r.get("momence_session_ids"), str)
    ]


def repair_string_encoded(row: dict, apply: bool) -> bool:
    """Re-store momence_session_ids / resolved_classes as proper JSON arrays.

    No NLP or CSV lookup needed -- the data is already correct, just stored
    in the wrong JSONB type. Returns True if the row was patched (or would
    be in dry-run), False on error.
    """
    rid = row["cover_request_id"]
    raw_ids = row.get("momence_session_ids")   # a str like "[123,456]"
    raw_cls = row.get("resolved_classes")       # a str like "[{...}]" or None

    try:
        ids_list = json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
        cls_list = json.loads(raw_cls) if isinstance(raw_cls, str) else raw_cls
    except (json.JSONDecodeError, TypeError) as e:
        print(f"    [FAIL] could not parse stored JSON string: {e}")
        return False

    print(f"    [repair] re-encoding {len(ids_list)} session ID(s) as JSONB array")
    if apply:
        payload: dict = {"momence_session_ids": ids_list}
        if cls_list is not None:
            payload["resolved_classes"] = cls_list
        try:
            sb_patch(
                "cover_requests",
                payload,
                match_params={"cover_request_id": f"eq.{rid}"},
            )
            print("    REPAIRED")
        except Exception as e:
            print(f"    [FAIL] PATCH failed: {e}")
            return False
    else:
        print("    [DRY RUN] would PATCH to fix JSONB string encoding")
    return True


def fetch_channel_name(channel_id: str | None) -> str:
    if not channel_id:
        return ""
    rows = sb_get(
        "whatsapp_channels",
        params={
            "whatsapp_channel_id": f"eq.{channel_id}",
            "select": "channel_name",
            "limit": "1",
        },
    )
    if rows:
        return rows[0].get("channel_name") or ""
    return ""


def reparse_message(parser: NLPParser, row: dict) -> "ParseResult | None":
    """Re-run the NLP parser on the stored raw_message."""
    raw = row.get("raw_message") or ""
    if not raw.strip():
        return None
    sender_name = row.get("requesting_teacher_name_raw") or None
    msg_ts = row.get("message_timestamp")
    msg_date = parse_iso_date(msg_ts) if msg_ts else None
    channel_name = fetch_channel_name(row.get("whatsapp_channel_id"))
    return parser.parse(
        message_text=raw,
        channel_name=channel_name,
        message_date=msg_date,
        sender_name=sender_name,
    )


def resolve_via_parsed_result(result, classes) -> list:
    """Same logic as cover_processor._resolve_classes_for_result, inlined.

    Now passes through cover_groups (2026-05-16+) so the resolver matches
    per-clause and avoids the cross-join over-match - keep this in lock-step
    with cover_processor.py's version.
    """
    if getattr(result, "message_type", None) != "request":
        return []
    dates = list(result.class_dates or [])
    if not dates and result.class_date:
        dates = [result.class_date]
    if not dates:
        return []
    times = list(result.class_times or [])
    if not times and result.class_time:
        times = [result.class_time]
    studios = list(result.studios or [])
    if not studios and result.studio:
        studios = [result.studio]
    disciplines = list(result.discipline_codes or [])
    if not disciplines and result.discipline_code:
        disciplines = [result.discipline_code]

    # Convert cover_groups dicts to objects, mirroring cover_processor.
    groups: list[CoverRequestGroup] = []
    for g in (getattr(result, "cover_groups", None) or []):
        try:
            g_dates = []
            for d_iso in g.get("dates", []):
                try: g_dates.append(_date.fromisoformat(d_iso))
                except (ValueError, TypeError): pass
            g_times = []
            for t_iso in g.get("times", []):
                try:
                    t_clean = (t_iso or "").strip()
                    if len(t_clean) == 5:
                        t_clean = t_clean + ":00"
                    g_times.append(_time.fromisoformat(t_clean))
                except (ValueError, TypeError): pass
            groups.append(CoverRequestGroup(
                dates=g_dates,
                times=g_times,
                studios=list(g.get("studios") or []),
                disciplines=list(g.get("disciplines") or []),
            ))
        except Exception as e:  # pragma: no cover - defensive
            print(f"    [backfill] skipping malformed cover_group: {e}")

    query = CoverRequestQuery(
        groups=groups,
        dates=dates,
        times=times,
        studios=studios,
        disciplines=disciplines,
    )
    return resolve_request_to_classes(query, classes)


def fallback_query_from_singulars(row: dict) -> CoverRequestQuery | None:
    """When re-parsing fails, fall back to the singular fields stored on
    the cover_request itself."""
    cd = parse_iso_date(row.get("class_date"))
    if not cd:
        return None
    times = []
    ct = row.get("class_time")
    if ct:
        try:
            from datetime import time as _time
            times.append(_time.fromisoformat(ct[:8]))
        except ValueError:
            pass
    studios = [row["studio"]] if row.get("studio") else []
    disciplines = [row["discipline_code"]] if row.get("discipline_code") else []
    return CoverRequestQuery(
        dates=[cd],
        times=times,
        studios=studios,
        disciplines=disciplines,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Write changes back to Supabase (default: dry run).")
    ap.add_argument("--limit", type=int, default=None,
                    help="Only process the first N rows (default: all).")
    ap.add_argument("--no-reparse", action="store_true",
                    help="Skip the Claude re-parse and use only the singular "
                         "fields stored on cover_requests.")
    ap.add_argument("--max-matches", type=int, default=10,
                    help="Skip rows where the resolver returns more than N "
                         "matches (default: 10). Context-only messages with no "
                         "time/studio/discipline can match dozens of classes; "
                         "this cap prevents over-broad patches.")
    args = ap.parse_args()

    print("=== Backfill resolved classes ===")
    print(f"Mode       : {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Reparse    : {'no' if args.no_reparse else 'yes (uses Claude)'}")
    print(f"Limit      : {args.limit or 'all'}")
    print(f"Max matches: {args.max_matches}")
    print()

    # -- Phase 0: repair JSONB string-encoding bug ---------------------------
    # cover_processor.py used json.dumps() before 2026-05-13, causing
    # momence_session_ids / resolved_classes to be stored as JSON strings
    # instead of JSON arrays. Detect and repair those rows cheaply (no NLP).
    bad_rows = fetch_string_encoded_requests()
    repair_count = 0
    if bad_rows:
        print(f"Found {len(bad_rows)} record(s) with JSONB string-encoding bug "
              f"(cover_processor json.dumps issue). Repairing first ...")
        for br in bad_rows:
            rid = br["cover_request_id"]
            teacher = br.get("requesting_teacher_name_raw") or "?"
            raw_first = (br.get("raw_message") or "").replace("\n", " ").strip()[:60]
            print(f"  {rid}  {teacher}: {raw_first}")
            ok = repair_string_encoded(br, apply=args.apply)
            if ok:
                repair_count += 1
        print()

    rows = fetch_unresolved_requests(limit=args.limit)
    print(f"Found {len(rows)} cover_request(s) needing resolution.\n")

    if not rows and not bad_rows:
        print("Nothing to do.")
        return 0

    if not rows:
        print("=" * 60)
        print(f"Done. repaired={repair_count}  updated=0  "
              f"skipped_no_match=0  failed=0")
        if not args.apply:
            print("\nDRY RUN -- re-run with --apply to actually update Supabase.")
        return 0

    print("Loading momence_classes_future.csv ...")
    future_classes = load_future_classes()
    print(f"  {len(future_classes)} future classes loaded.")

    # Also load the latest past-sessions CSV so historical requests
    # (for classes that have already passed) can be resolved.
    past_csvs = sorted(
        MOMENCE_DATA_DIR.glob("momence_classes_p_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if past_csvs:
        past_csv = past_csvs[0]
        print(f"Loading past-sessions CSV: {past_csv.name} ...")
        past_classes = load_future_classes(past_csv)
        print(f"  {len(past_classes)} past classes loaded.")
    else:
        print("[WARN] No momence_classes_p_*.csv found in MOMENCE_DATA_DIR -- "
              "historical requests may not resolve.")
        past_classes = []

    classes = future_classes + past_classes
    print(f"  {len(classes)} total classes in pool.\n")

    parser = NLPParser() if not args.no_reparse else None
    if parser is not None:
        print(f"Using NLP parser model: {parser.model}\n")

    counts = {"updated": 0, "skipped_no_match": 0, "failed": 0}

    for i, row in enumerate(rows, 1):
        rid = row["cover_request_id"]
        teacher = row.get("requesting_teacher_name_raw") or "?"
        raw_first = (row.get("raw_message") or "").replace("\n", " ").strip()[:80]
        print(f"[{i}/{len(rows)}] {rid}  {teacher}: {raw_first}")

        try:
            matches = []
            if parser is not None:
                result = reparse_message(parser, row)
                if result is None:
                    print("    [WARN] empty raw_message -- falling back to singular")
                else:
                    matches = resolve_via_parsed_result(result, classes)
            if not matches:
                # Fallback to the singular fields already on the cover_request.
                fallback_q = fallback_query_from_singulars(row)
                if fallback_q is not None:
                    matches = resolve_request_to_classes(fallback_q, classes)
                    if matches:
                        print(f"    [fallback] resolved via singular fields -> "
                              f"{len(matches)} class(es)")
                else:
                    print("    [skip] no usable date/studio/discipline")

            if not matches:
                counts["skipped_no_match"] += 1
                print()
                continue

            if len(matches) > args.max_matches:
                print(f"    [skip] {len(matches)} matches exceeds --max-matches "
                      f"{args.max_matches} -- likely a context-only message; "
                      f"skipping to avoid over-broad patch.")
                counts["skipped_no_match"] += 1
                print()
                continue

            momence_ids = [m.momence_session_id for m in matches]
            snapshots = [m.to_snapshot_dict() for m in matches]
            now_iso = datetime.now(timezone.utc).isoformat()

            print(f"    matched {len(matches)} class(es): "
                  f"{[m.date.isoformat() + ' ' + m.start_time.strftime('%H:%M') for m in matches[:5]]}"
                  f"{' ...' if len(matches) > 5 else ''}")
            print(f"    momence_session_ids: {momence_ids}")

            if args.apply:
                payload = {
                    "momence_session_ids": momence_ids,
                    "resolved_classes": snapshots,
                    "classes_resolved_at": now_iso,
                }
                sb_patch(
                    "cover_requests",
                    payload,
                    match_params={"cover_request_id": f"eq.{rid}"},
                )
                print("    UPDATED")
            else:
                print("    [DRY RUN] would PATCH cover_requests with the above")
            counts["updated"] += 1
        except Exception as e:
            counts["failed"] += 1
            print(f"    [FAIL] {type(e).__name__}: {e}")
            traceback.print_exc(file=sys.stdout)
        print()

    print("=" * 60)
    print(f"Done. repaired={repair_count}  updated={counts['updated']}  "
          f"skipped_no_match={counts['skipped_no_match']}  "
          f"failed={counts['failed']}")
    if not args.apply:
        print("\nDRY RUN -- re-run with --apply to actually update Supabase.")
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
