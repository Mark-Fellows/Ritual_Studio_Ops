"""
dedup_existing_requests.py — Stage 3 Phase 2, one-shot backfill.

Walks every cover_request that has momence_session_ids set and
status in OPEN, and for each row checks whether an EARLIER OPEN
cover_request from the same teacher overlaps it >= DEDUP_OVERLAP_THRESHOLD.
If so, the LATER row is marked as duplicate_of the earlier one and the
earlier row's reminder_count is bumped.

Usage
-----
    python stage3/dedup_existing_requests.py                # DRY RUN
    python stage3/dedup_existing_requests.py --apply        # write
    python stage3/dedup_existing_requests.py --threshold 0.8

Idempotent: rows already marked duplicate_of are skipped on re-run.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "stage2"))

from config import sb_get, sb_patch
from cover_processor import (
    DEDUP_OVERLAP_THRESHOLD,
    DEDUP_LOOKBACK_DAYS,
    _DEDUP_OPEN_STATUSES,
    _overlap_coefficient,
)


# Use the same statuses cover_processor uses, plus also include rows that
# previously matched and got status='duplicate_of' so we can detect when a
# row was re-classified incorrectly. They're skipped as candidate parents.
_OPEN_OR_DUP = list(_DEDUP_OPEN_STATUSES) + ["duplicate_of"]


def fetch_dedupable_rows() -> list[dict]:
    """Every row with momence_session_ids set, in date order."""
    return sb_get(
        "cover_requests",
        params={
            "select": (
                "cover_request_id,requesting_teacher_id,requesting_teacher_name_raw,"
                "momence_session_ids,reminder_count,status,parent_cover_request_id,"
                "message_timestamp,raw_message"
            ),
            "momence_session_ids": "not.is.null",
            "status": f"in.({','.join(_OPEN_OR_DUP)})",
            "order": "message_timestamp.asc",
        },
    )


def short_msg(row: dict, n: int = 60) -> str:
    s = (row.get("raw_message") or "").replace("\n", " ").strip()
    return s[:n] + ("…" if len(s) > n else "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Write changes back to Supabase (default: dry run).")
    ap.add_argument("--threshold", type=float, default=DEDUP_OVERLAP_THRESHOLD,
                    help=f"Overlap-coefficient threshold (default {DEDUP_OVERLAP_THRESHOLD}).")
    ap.add_argument("--lookback-days", type=int, default=DEDUP_LOOKBACK_DAYS,
                    help=f"Window for candidate parents (default {DEDUP_LOOKBACK_DAYS}).")
    args = ap.parse_args()

    print("=== Phase 2 dedup backfill ===")
    print(f"Mode      : {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Threshold : {args.threshold}")
    print(f"Lookback  : {args.lookback_days} days")
    print()

    rows = fetch_dedupable_rows()
    print(f"Found {len(rows)} cover_request(s) with momence_session_ids.")
    if not rows:
        return 0

    # Index by teacher. Pre-pass: build name -> id mapping so a row that
    # has only the lowercased teacher name resolved still ends up in the
    # same bucket as rows where the id has been resolved. Without this,
    # cb81640b (Mikela Meli with id) and d1bde23e (Mikela Meli without id)
    # ended up in different groups and dedup missed them.
    name_to_id: dict[str, str] = {}
    for r in rows:
        nm = (r.get("requesting_teacher_name_raw") or "").strip().lower()
        tid = r.get("requesting_teacher_id")
        if nm and tid and nm not in name_to_id:
            name_to_id[nm] = tid

    def key_for(row):
        nm = (row.get("requesting_teacher_name_raw") or "").strip().lower()
        tid = row.get("requesting_teacher_id")
        if tid:
            return tid
        if nm and nm in name_to_id:
            return name_to_id[nm]  # collapse name-only row into the id bucket
        return "name:" + nm

    counts = {"linked": 0, "skipped_already_dup": 0, "no_match": 0, "failed": 0}
    bumps_by_parent: dict[str, list] = {}

    # Walk rows in chronological order. For each row that's NOT already a
    # duplicate, look back at earlier rows from the same teacher and find
    # the highest-overlap match within the lookback window.
    by_teacher: dict[str, list[dict]] = {}
    for r in rows:
        by_teacher.setdefault(key_for(r), []).append(r)

    for tk, group in by_teacher.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda r: r.get("message_timestamp") or "")
        for i, row in enumerate(group):
            if row.get("status") == "duplicate_of":
                counts["skipped_already_dup"] += 1
                continue
            new_set = set(row.get("momence_session_ids") or [])
            if not new_set:
                continue
            # Compare to every earlier OPEN row in the lookback window
            best, best_score = None, 0.0
            try:
                row_ts = datetime.fromisoformat(
                    (row.get("message_timestamp") or "").replace("Z", "+00:00")
                )
            except Exception:
                row_ts = None
            for j in range(i):
                cand = group[j]
                if cand.get("status") == "duplicate_of":
                    continue
                if row_ts:
                    try:
                        cand_ts = datetime.fromisoformat(
                            (cand.get("message_timestamp") or "").replace("Z", "+00:00")
                        )
                        if (row_ts - cand_ts).days > args.lookback_days:
                            continue
                    except Exception:
                        pass
                cand_set = cand.get("momence_session_ids") or []
                if not cand_set:
                    continue
                score = _overlap_coefficient(new_set, cand_set)
                if score > best_score:
                    best, best_score = cand, score

            if not best or best_score < args.threshold:
                counts["no_match"] += 1
                continue

            # Found a parent — apply (or report)
            new_id = row["cover_request_id"]
            parent_id = best["cover_request_id"]
            parent_name = best.get("requesting_teacher_name_raw") or "?"
            print(f"[link] '{short_msg(row, 50)}' ({row['cover_request_id'][:8]})")
            print(f"   ↳ duplicate_of '{short_msg(best, 50)}' ({parent_id[:8]})")
            print(f"   overlap={best_score:.2f}   teacher={parent_name}")

            if args.apply:
                try:
                    sb_patch(
                        "cover_requests",
                        {"status": "duplicate_of", "parent_cover_request_id": parent_id},
                        match_params={"cover_request_id": f"eq.{new_id}"},
                    )
                    bumps_by_parent.setdefault(parent_id, []).append({
                        "child_id": new_id,
                        "ts": row.get("message_timestamp"),
                    })
                    counts["linked"] += 1
                    print("   ✓ UPDATED child")
                except Exception as e:
                    counts["failed"] += 1
                    print(f"   [FAIL] child PATCH: {e}")
            else:
                counts["linked"] += 1
                print("   [DRY RUN] would PATCH child + bump parent reminder_count")
            print()

    # Apply parent bumps in a second pass so the increments are correct even
    # when one parent is referenced by multiple children.
    if args.apply and bumps_by_parent:
        print("--- Applying parent reminder_count bumps ---")
        for parent_id, kids in bumps_by_parent.items():
            try:
                # Re-read current count to be safe
                cur = sb_get(
                    "cover_requests",
                    params={
                        "select": "reminder_count",
                        "cover_request_id": f"eq.{parent_id}",
                        "limit": "1",
                    },
                )
                cur_count = (cur[0].get("reminder_count") if cur else 0) or 0
                latest_ts = max(k["ts"] for k in kids if k["ts"]) if any(
                    k["ts"] for k in kids) else None
                bump = {"reminder_count": cur_count + len(kids)}
                if latest_ts:
                    bump["last_reminder_at"] = latest_ts
                sb_patch(
                    "cover_requests",
                    bump,
                    match_params={"cover_request_id": f"eq.{parent_id}"},
                )
                print(f"  parent {parent_id[:8]}  reminder_count {cur_count} → "
                      f"{cur_count + len(kids)}  ({len(kids)} children)")
            except Exception as e:
                counts["failed"] += 1
                print(f"  [FAIL] parent {parent_id[:8]}: {e}")

    print()
    print("=" * 60)
    print(f"Done. linked={counts['linked']}  no_match={counts['no_match']}  "
          f"already_duplicate={counts['skipped_already_dup']}  "
          f"failed={counts['failed']}")
    if not args.apply:
        print("\nDRY RUN — re-run with --apply to actually update Supabase.")
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
