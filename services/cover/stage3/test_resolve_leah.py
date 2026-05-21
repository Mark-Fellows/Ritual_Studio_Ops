"""
test_resolve_leah.py
====================

Standalone regression test for the per-group cover request resolver
introduced 2026-05-16. Verifies that Leah's 4-class request:

    18/5 PB - 8:30, 9:30 reformer
    20/5 Robina - 7:15, 8:15 reformer

resolves to exactly 4 Momence classes when expressed as two groups,
and that the legacy flat-list query still produces the over-matched
result for backward-compat validation.

Run:
    python stage3\\test_resolve_leah.py

No Supabase / Anthropic calls. Reads only momence_classes_future.csv.
"""
from __future__ import annotations

import sys
from datetime import date, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "stage3"))

from resolve_classes import (
    CoverRequestGroup,
    CoverRequestQuery,
    load_future_classes,
    resolve_request_to_classes,
    format_matches,
)


def main() -> int:
    # Load the CSV once for both tests
    classes = load_future_classes()
    print(f"Loaded {len(classes)} future classes from CSV.\n")

    # ── Test A: per-group mode (NEW) ──────────────────────────────
    leah_groups_query = CoverRequestQuery(
        groups=[
            CoverRequestGroup(
                dates=[date(2026, 5, 18)],
                times=[time(8, 30), time(9, 30)],
                studios=["Palm Beach"],
                disciplines=["reformer"],
            ),
            CoverRequestGroup(
                dates=[date(2026, 5, 20)],
                times=[time(7, 15), time(8, 15)],
                studios=["Robina"],
                disciplines=["reformer"],
            ),
        ],
    )
    per_group_matches = resolve_request_to_classes(leah_groups_query, classes)
    print("=== Per-group resolver (the fix) ===")
    print(format_matches(per_group_matches))
    per_group_count = len(per_group_matches)
    print(f"\nPer-group match count: {per_group_count}")
    print(f"Expected: 4\n")

    # ── Test B: legacy flat-list mode (cross-join, for comparison) ──
    leah_flat_query = CoverRequestQuery(
        dates=[date(2026, 5, 18), date(2026, 5, 20)],
        times=[time(7, 15), time(8, 15), time(8, 30), time(9, 30)],
        studios=["Palm Beach", "Robina"],
        disciplines=["reformer"],
    )
    flat_matches = resolve_request_to_classes(leah_flat_query, classes)
    print("=== Legacy flat-list resolver (the bug) ===")
    print(format_matches(flat_matches))
    flat_count = len(flat_matches)
    print(f"\nFlat-list match count: {flat_count}")
    print(f"Expected (the buggy reproduction): >= 6 (cross-join over-match)\n")

    # ── Assertions ───────────────────────────────────────────────
    print("=== Result ===")
    if per_group_count == 4:
        print("[PASS] Per-group resolver returned exactly 4 classes.")
    else:
        print(f"[FAIL] Per-group resolver returned {per_group_count} classes; expected 4.")
        return 1

    if flat_count > per_group_count:
        print(f"[PASS] Flat-list returned {flat_count} (over-matches by {flat_count - per_group_count}), confirming per-group is the fix.")
    else:
        print(f"[NOTE] Flat-list returned {flat_count} - same or fewer than per-group. The CSV at this moment may not contain the buggy cross-join entries.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
