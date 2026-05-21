#!/usr/bin/env python3
"""
archive_old_files.py
====================
Applies a tiered retention policy to dated Momence pipeline files.

Retention tiers
---------------
  Last 8 days          : keep every file
  8 days to 90 days    : keep the most recent file per ISO week, per file family
  91 days and older    : keep the most recent file per calendar month, per file family

Files outside the policy are moved to Archive\old_data\For_Deletion for
manual review before deletion.

File families managed
---------------------
  Log_files/Run_Momence_Chain_*.log
  Log_files/momence_scraper_log_*.txt
  momence_classes_f_*.csv
  momence_classes_p_*.csv
  momence_classes_lite_*.csv
  momence_all_classes_*.csv
  momence_full_classes_*.csv
  Momence_class_customers_all_*.csv
  RUN_REPORT_*.md

Usage
-----
  python archive_old_files.py          # normal run
  python archive_old_files.py --dry-run  # print what would be moved, move nothing
"""

import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.resolve()
DEST_DIR = BASE_DIR / "Archive" / "old_data" / "For_Deletion"

KEEP_DAILY_DAYS  = 8   # keep every file from the last N days
KEEP_WEEKLY_DAYS = 90  # keep 1-per-week for files N days old; monthly beyond that

TODAY = date.today()
DRY_RUN = "--dry-run" in sys.argv


# ---------------------------------------------------------------------------
# Date extraction helpers
# ---------------------------------------------------------------------------

def extract_date_yyyymmdd(name: str) -> Optional[date]:
    """
    Extracts a date from filenames containing an 8-digit YYYYMMDD block.
    e.g. Run_Momence_Chain_20260512_020004.log  -> 2026-05-12
         RUN_REPORT_20260512.md               -> 2026-05-12
    """
    m = re.search(r'(\d{4})(\d{2})(\d{2})', name)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def extract_date_spaced(name: str) -> Optional[date]:
    """
    Extracts a date from filenames containing a 'YYYY MM DD' space-separated block.
    e.g. momence_classes_f_2026 04 01 02 14.csv  -> 2026-04-01
    """
    m = re.search(r'(\d{4}) (\d{2}) (\d{2})', name)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# File family definitions
# ---------------------------------------------------------------------------
# Each entry describes one family of dated files.  Files within the same
# family compete against each other for the weekly/monthly keeper slot.

FILE_FAMILIES = [
    {
        "label":        "Chain run logs",
        "dir":          BASE_DIR / "Log_files",
        "glob":         "Run_Momence_Chain_*.log",
        "extract_date": extract_date_yyyymmdd,
    },
    {
        "label":        "Scraper logs",
        "dir":          BASE_DIR / "Log_files",
        "glob":         "momence_scraper_log_*.txt",
        "extract_date": extract_date_spaced,
    },
    {
        "label":        "Future classes CSV",
        "dir":          BASE_DIR,
        "glob":         "momence_classes_f_*.csv",
        "extract_date": extract_date_spaced,
    },
    {
        "label":        "Past classes CSV",
        "dir":          BASE_DIR,
        "glob":         "momence_classes_p_*.csv",
        "extract_date": extract_date_spaced,
    },
    {
        "label":        "Lite classes CSV",
        "dir":          BASE_DIR,
        "glob":         "momence_classes_lite_*.csv",
        "extract_date": extract_date_spaced,
    },
    {
        "label":        "All classes CSV",
        "dir":          BASE_DIR,
        "glob":         "momence_all_classes_*.csv",
        "extract_date": extract_date_spaced,
    },
    {
        "label":        "Full classes CSV",
        "dir":          BASE_DIR,
        "glob":         "momence_full_classes_*.csv",
        "extract_date": extract_date_spaced,
    },
    {
        "label":        "Class customers CSV",
        "dir":          BASE_DIR,
        "glob":         "Momence_class_customers_all_*.csv",
        "extract_date": extract_date_spaced,
    },
    {
        "label":        "Run reports",
        "dir":          BASE_DIR,
        "glob":         "RUN_REPORT_*.md",
        "extract_date": extract_date_yyyymmdd,
    },
]


# ---------------------------------------------------------------------------
# Retention logic
# ---------------------------------------------------------------------------

def retention_bucket(file_date: date) -> Tuple[str, tuple]:
    """
    Returns (tier, bucket_key) for a given file date.
      'daily'   -> key = the date itself        (always kept, no competition)
      'weekly'  -> key = (ISO year, ISO week)
      'monthly' -> key = (year, month)
    """
    age_days = (TODAY - file_date).days
    if age_days < KEEP_DAILY_DAYS:
        return ('daily', (file_date,))
    elif age_days < KEEP_WEEKLY_DAYS:
        iso = file_date.isocalendar()
        return ('weekly', (iso.year, iso.week))
    else:
        return ('monthly', (file_date.year, file_date.month))


def files_to_archive(entries: List[Tuple[date, Path]]) -> List[Path]:
    """
    Given a list of (file_date, path) for one family, returns the paths
    that should be moved to For_Deletion.

    Within each weekly or monthly bucket the most recent file (by date) is
    kept; duplicates within the same bucket are archived.  All files in the
    daily window are kept unconditionally.
    """
    buckets: dict = defaultdict(list)
    for file_date, path in entries:
        tier, key = retention_bucket(file_date)
        buckets[(tier, key)].append((file_date, path))

    to_archive = []
    for (tier, key), group in buckets.items():
        if tier == 'daily':
            continue                        # keep everything in daily window
        group.sort(key=lambda x: x[0], reverse=True)   # most recent first
        for _, path in group[1:]:           # drop all but the most recent
            to_archive.append(path)

    return to_archive


# ---------------------------------------------------------------------------
# Name collision helper
# ---------------------------------------------------------------------------

def safe_dest(path: Path, dest_dir: Path) -> Path:
    """Returns a destination path that does not already exist."""
    dest = dest_dir / path.name
    if not dest.exists():
        return dest
    stem, suffix = path.stem, path.suffix
    i = 1
    while dest.exists():
        dest = dest_dir / f"{stem}_{i}{suffix}"
        i += 1
    return dest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> int:
    if DRY_RUN:
        print("[archive_old_files] DRY RUN — no files will be moved.\n")

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    total_moved = 0
    total_kept  = 0

    for family in FILE_FAMILIES:
        search_dir: Path = family["dir"]
        if not search_dir.exists():
            continue

        files = list(search_dir.glob(family["glob"]))
        if not files:
            continue

        # Parse dates; skip files whose names don't contain a recognisable date
        dated: List[Tuple[date, Path]] = []
        for path in files:
            d = family["extract_date"](path.name)
            if d is not None:
                dated.append((d, path))

        if not dated:
            continue

        to_move = files_to_archive(dated)
        kept = len(dated) - len(to_move)

        print(f"\n{family['label']}  ({len(dated)} files — keeping {kept}, archiving {len(to_move)})")

        for path in sorted(to_move, key=lambda p: p.name):
            dest = safe_dest(path, DEST_DIR)
            if DRY_RUN:
                print(f"  [DRY RUN] would move: {path.name}")
            else:
                shutil.move(str(path), str(dest))
                print(f"  ARCHIVED: {path.name}")
            total_moved += 1

        total_kept += kept

    print(f"\n[archive_old_files] Complete — {total_kept} file(s) retained, "
          f"{total_moved} file(s) {'would be ' if DRY_RUN else ''}moved to For_Deletion.")
    return total_moved


if __name__ == "__main__":
    run()
