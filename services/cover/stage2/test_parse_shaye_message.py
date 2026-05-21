"""
test_parse_shaye_message.py — Phase 1b end-to-end check.

Parses Shaye's 13 April 2026 message with the updated NLP parser and verifies:
  1. class_dates is now populated as an array (not just class_date),
  2. Feeding that array through stage3/resolve_classes returns the
     14 Momence classes she's actually asking to be covered.

Standalone — does not write to Supabase. Reads ANTHROPIC_API_KEY from .env.
"""

from __future__ import annotations

import sys
from datetime import date, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "stage3"))

from nlp_parser import NLPParser
from resolve_classes import (
    CoverRequestQuery,
    load_future_classes,
    resolve_request_to_classes,
    format_matches,
)


# Shaye's actual 13 April 2026 message text (taken from diag_shaye_records.txt).
# The CSV-stored raw_message is truncated at 140 chars; this version is the
# fuller text reconstructed from the message context.
SHAYE_MESSAGE = """Hey guys! I'll be away in indo from May 29th- June 19th.

I'm looking for covers for Mat Pilates all at robina studio:

Tuesday 2nd June- 5:15am & 7:30am
Tuesday 9th June- 5:15am & 7:30am
Tuesday 16th June - 5:15am & 7:30am
Friday 29th May - 5:15am & 7:30am
Friday 5th June - 5:15am & 7:30am
Friday 12th June - 5:15am & 7:30am
Friday 19th June - 5:15am & 7:30am

Thanks!"""

EXPECTED_DATES = [
    date(2026, 5, 29),
    date(2026, 6, 2),
    date(2026, 6, 5),
    date(2026, 6, 9),
    date(2026, 6, 12),
    date(2026, 6, 16),
    date(2026, 6, 19),
]


def main() -> None:
    parser = NLPParser()
    print(f"Calling Claude with model={parser.model}…\n")
    result = parser.parse(
        message_text=SHAYE_MESSAGE,
        channel_name="RITUAL TEACHERS",
        message_date=date(2026, 4, 13),
        sender_name="Shaye",
    )

    print("--- Parse result ---")
    print(f"  message_type      : {result.message_type}")
    print(f"  confidence_score  : {result.confidence_score}")
    print(f"  teacher_name      : {result.teacher_name}")
    print(f"  class_date (1st)  : {result.class_date}")
    print(f"  class_dates (all) : {result.class_dates}")
    print(f"  class_times       : {result.class_times}")
    print(f"  studios           : {result.studios}")
    print(f"  discipline_codes  : {result.discipline_codes}")
    print(f"  est_class_count   : {result.estimated_class_count}")
    print(f"  parse_notes       : {result.parse_notes}")

    extracted = sorted(result.class_dates or [])
    print(f"\n  Extracted dates ({len(extracted)}): {[d.isoformat() for d in extracted]}")
    print(f"  Expected dates  ({len(EXPECTED_DATES)}): {[d.isoformat() for d in EXPECTED_DATES]}")
    print(f"  Match           : {extracted == EXPECTED_DATES}")

    if not result.class_dates or not result.class_times:
        print("\nABORT — parser returned no dates or times; nothing to resolve.")
        return

    print("\n--- Resolving against momence_classes_future.csv ---")
    classes = load_future_classes()
    query = CoverRequestQuery(
        dates=result.class_dates,
        times=result.class_times,
        studios=result.studios or [],
        disciplines=result.discipline_codes or [],
    )
    matches = resolve_request_to_classes(query, classes)
    print(format_matches(matches))

    print(f"\n--- Persistable momence_session_ids ({len(matches)}) ---")
    print([m.momence_session_id for m in matches])


if __name__ == "__main__":
    main()
