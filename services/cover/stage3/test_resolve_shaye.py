"""
test_resolve_shaye.py — exercise resolve_classes against Shaye's known case.

Standalone — no DB writes, no Anthropic calls. Run directly:

    python stage3/test_resolve_shaye.py

Shaye's 13 April 2026 message:
  "Hey guys! I'll be away in indo from May 29th- June 19th.
   I'm looking for covers for Mat Pilates all at robina studio:
   Tuesday 2nd June- 5:15am & 7:30am
   Tuesday 9th June- 5:15am & 7:30am
   Tuesday 16th June - 5:15am & 7:30am
   …"

Her cover_requests rows recorded est_classes=14, which suggests 7 days x 2
times. The Tuesdays in [29 May, 19 June] are 2/9/16 June (3 dates), the
Fridays in that window are 29 May and 5/12/19 June (4 dates) — total 7
dates x 2 times = 14 classes. Both are tested below.
"""

import sys
from datetime import date, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from resolve_classes import (
    CoverRequestQuery,
    load_future_classes,
    resolve_request_to_classes,
    format_matches,
)


def main() -> None:
    classes = load_future_classes()
    print(f"Loaded {len(classes)} future classes from CSV.\n")

    # Case 1 — explicit Tuesdays only (the 6 classes Shaye literally listed).
    tuesdays = [date(2026, 6, 2), date(2026, 6, 9), date(2026, 6, 16)]
    q1 = CoverRequestQuery(
        dates=tuesdays,
        times=[time(5, 15), time(7, 30)],
        studios=["Robina"],
        disciplines=["mat_pilates"],
    )
    m1 = resolve_request_to_classes(q1, classes)
    print("=== Case 1: explicit Tuesdays (3 dates x 2 times → expecting 6) ===")
    print(format_matches(m1))
    print()

    # Case 2 — full date range she gave (29 May – 19 June). Mat Pilates at
    # Robina at 5:15 OR 7:30. Should pick up both Tuesdays AND Fridays.
    q2 = CoverRequestQuery(
        date_range_start=date(2026, 5, 29),
        date_range_end=date(2026, 6, 19),
        times=[time(5, 15), time(7, 30)],
        studios=["Robina"],
        disciplines=["mat_pilates"],
    )
    m2 = resolve_request_to_classes(q2, classes)
    print("=== Case 2: full range 29 May – 19 June, 5:15 or 7:30 (expecting 14) ===")
    print(format_matches(m2))
    print()

    # Case 3 — Same range, no time filter (any Mat Pilates at Robina).
    q3 = CoverRequestQuery(
        date_range_start=date(2026, 5, 29),
        date_range_end=date(2026, 6, 19),
        studios=["Robina"],
        disciplines=["mat_pilates"],
    )
    m3 = resolve_request_to_classes(q3, classes)
    print("=== Case 3: full range, ANY Mat Pilates time at Robina ===")
    print(format_matches(m3))
    print()

    # Stable session-id list — what we'd actually persist on the cover_request.
    print("=== Persistable momence_session_ids for Case 2 ===")
    print([c.momence_session_id for c in m2])


if __name__ == "__main__":
    main()
