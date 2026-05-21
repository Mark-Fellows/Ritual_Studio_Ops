"""
resolve_classes.py — Stage 3 (Phase 1a)
========================================
Resolves a parsed cover request into the concrete list of Momence classes
that the requesting teacher is asking to be covered.

Reads from data/momence_classes_future.csv (refreshed nightly by the
existing Momence pipeline). Each match returns the durable Momence
``Class Number`` plus a snapshot of the row's metadata so the caller
can detect drift later (TBA teacher updates, time shifts of 15-30 min,
or class-type changes that the studio sometimes makes when no cover is
found).

This module is intentionally self-contained:
  * no Supabase calls,
  * no Anthropic calls,
  * no writes anywhere,

so it can be exercised standalone before being wired into
``cover_processor.py``.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Iterable

# ─────────────────────────────────────────────────────────────────────────────
# Constants — file path and lookup tables
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = PROJECT_ROOT / "data" / "momence_classes_future.csv"

# Studio short-name → list of substrings that must appear in the CSV ``Location``
# column for a row to count as that studio. The CSV has multiple rooms per
# physical studio (e.g. "Robina Studio: Easy T Centre…" and "Reformer studio
# (RS)" are both at Robina), so we match on either the long name or a venue
# code in parentheses.
STUDIO_LOCATION_SUBSTRINGS: dict[str, tuple[str, ...]] = {
    "Robina": ("Robina", "(RS)"),
    "Palm Beach": ("Palm Beach", "(PB)"),
}

# CSV ``Class Name`` substring → discipline code emitted by the NLP parser.
# Order matters: the first matching pattern wins, so the more-specific
# patterns (e.g. ``mat`` + ``pilates``) are listed before the generic
# ``pilates`` and ``yoga``.
DISCIPLINE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("reformer",        "reformer"),       # "Reformer", "Jump Board Reformer"
    ("pilates mat",     "mat_pilates"),    # "Pilates Mat", "Pilates Mat Teacher Training"
    ("mat pilates",     "mat_pilates"),
    ("power pilates",   "mat_pilates"),
    ("free pilates",    "mat_pilates"),
    ("yin",             "yin"),            # "Yin"
    ("barre",           "barre"),          # "Barre"
    ("vinyasa",         "yoga"),           # "Vinyasa Yoga"
    ("yoga",            "yoga"),           # generic yoga catch-all (must come AFTER yin)
)

# How many minutes either side of the requested time still counts as a match.
# Matches Mark's note that Momence may shift a class by 15 or 30 minutes when
# no cover is found.
DEFAULT_TIME_TOLERANCE_MIN = 30


# ─────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FutureClass:
    """One row from momence_classes_future.csv, parsed."""

    momence_session_id: int          # CSV ``Class Number`` — durable identity
    class_name: str                  # CSV ``Class Name`` (e.g. "Pilates Mat")
    discipline: str                  # mapped code (e.g. "mat_pilates"); "" if unmapped
    weekday: str                     # CSV ``Weekday`` (e.g. "Tue")
    date: date
    start_time: time
    end_time: time
    location: str                    # full CSV ``Location`` string
    studio: str                      # mapped short name (e.g. "Robina"); "" if unmapped
    teacher: str                     # CSV ``Teacher`` (often "NA")
    substitute: str                  # CSV ``Substitute`` (often "NA")
    capacity: int | None
    signups: int | None

    def to_snapshot_dict(self) -> dict:
        """JSON-serialisable snapshot for storing alongside the request."""
        return {
            "momence_session_id": self.momence_session_id,
            "class_name": self.class_name,
            "discipline": self.discipline,
            "weekday": self.weekday,
            "date": self.date.isoformat(),
            "start_time": self.start_time.isoformat(timespec="minutes"),
            "end_time": self.end_time.isoformat(timespec="minutes"),
            "studio": self.studio,
            "location": self.location,
            "teacher": self.teacher,
            "substitute": self.substitute,
            "capacity": self.capacity,
            "signups": self.signups,
        }


@dataclass
class CoverRequestGroup:
    """
    One specific (date set, studio set, time set, discipline set) clause
    of a cover request.

    Many real WhatsApp messages have multiple clauses that should NOT be
    cross-joined when matched against Momence. For example:

        "18/5 PB - 8:30, 9:30 reformer
         20/5 Robina - 7:15, 8:15 reformer"

    is two groups:
        Group 1: dates=[18/5], studios=[Palm Beach], times=[08:30, 09:30], disciplines=[reformer]
        Group 2: dates=[20/5], studios=[Robina],     times=[07:15, 08:15], disciplines=[reformer]

    Cross-joining the flat sets {18/5, 20/5} x {PB, Robina} x {7:15, 8:15, 8:30, 9:30}
    yields 16 candidate (date, studio, time) tuples - of which only 4 actually
    correspond to classes Leah is asking cover for. Per-group matching avoids
    that explosion.

    Backward-compat note: an empty group (no dates / no times / etc.) is
    treated as "any" for that field, matching the legacy CoverRequestQuery
    semantics.
    """

    dates: list[date] = field(default_factory=list)
    times: list[time] = field(default_factory=list)
    studios: list[str] = field(default_factory=list)
    disciplines: list[str] = field(default_factory=list)


@dataclass
class CoverRequestQuery:
    """Filter inputs for resolve_request_to_classes.

    Preferred input is ``groups`` (one CoverRequestGroup per clause of
    the original message). When groups is non-empty, resolve_request_to_classes
    matches each group independently and returns the union (deduped by
    momence_session_id).

    The flat ``dates``, ``date_range_*``, ``times``, ``studios``,
    ``disciplines`` fields are retained for backward compatibility with
    older callers and as a fallback when grouping cannot be inferred.
    They are ignored entirely if ``groups`` is non-empty.
    """

    # Preferred: list of per-clause groups (added 2026-05-16 to fix
    # the cross-join over-matching documented above).
    groups: list[CoverRequestGroup] = field(default_factory=list)

    # Specific dates (preferred). When non-empty, date_range_* are ignored.
    dates: list[date] = field(default_factory=list)
    # OR a date range — every weekday in [start, end] inclusive is considered
    # if dates is empty. Used when the message says "I'm away May 29 – June 19".
    date_range_start: date | None = None
    date_range_end: date | None = None
    # Specific clock times (start of class). Empty = any time.
    times: list[time] = field(default_factory=list)
    # Studio short names — matched against STUDIO_LOCATION_SUBSTRINGS. Empty = any.
    studios: list[str] = field(default_factory=list)
    # Discipline codes — matched against DISCIPLINE_PATTERNS. Empty = any.
    disciplines: list[str] = field(default_factory=list)
    # Tolerance (minutes) around the requested time(s).
    time_tolerance_min: int = DEFAULT_TIME_TOLERANCE_MIN


# ─────────────────────────────────────────────────────────────────────────────
# Parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

_TIME_RANGE_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*$")


def _parse_csv_date(s: str) -> date | None:
    """CSV uses "07 May 2026"."""
    s = s.strip()
    try:
        return datetime.strptime(s, "%d %b %Y").date()
    except ValueError:
        return None


def _parse_csv_time_range(s: str) -> tuple[time, time] | None:
    """CSV uses "05:15 - 06:05"."""
    m = _TIME_RANGE_RE.match(s)
    if not m:
        return None
    sh, sm, eh, em = (int(g) for g in m.groups())
    try:
        return time(sh, sm), time(eh, em)
    except ValueError:
        return None


def _parse_int_or_none(s: str) -> int | None:
    s = (s or "").strip()
    if not s or s == "NA":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _classify_discipline(class_name: str) -> str:
    """Return discipline code for a CSV ``Class Name``, or '' if unrecognised."""
    n = (class_name or "").strip().lower()
    for needle, code in DISCIPLINE_PATTERNS:
        if needle in n:
            return code
    return ""


def _classify_studio(location: str) -> str:
    """Return short studio name for a CSV ``Location``, or '' if unrecognised."""
    if not location:
        return ""
    for short_name, substrings in STUDIO_LOCATION_SUBSTRINGS.items():
        if any(sub in location for sub in substrings):
            return short_name
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# CSV loading
# ─────────────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=4)
def _load_classes_cached(csv_path_str: str, _mtime: float) -> tuple[FutureClass, ...]:
    """Load and parse the CSV. Cached against (path, mtime)."""
    csv_path = Path(csv_path_str)
    out: list[FutureClass] = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cid = int((row.get("Class Number") or "").strip())
            except ValueError:
                continue
            cls_date = _parse_csv_date(row.get("Date") or "")
            if cls_date is None:
                continue
            time_range = _parse_csv_time_range(row.get("Time") or "")
            if time_range is None:
                continue
            start_t, end_t = time_range
            class_name = (row.get("Class Name") or "").strip()
            location = (row.get("Location") or "").strip()
            out.append(FutureClass(
                momence_session_id=cid,
                class_name=class_name,
                discipline=_classify_discipline(class_name),
                weekday=(row.get("Weekday") or "").strip(),
                date=cls_date,
                start_time=start_t,
                end_time=end_t,
                location=location,
                studio=_classify_studio(location),
                teacher=(row.get("Teacher") or "").strip(),
                substitute=(row.get("Substitute") or "").strip(),
                capacity=_parse_int_or_none(row.get("Capacity") or ""),
                signups=_parse_int_or_none(row.get("Signups") or ""),
            ))
    return tuple(out)


def load_future_classes(csv_path: Path | None = None) -> tuple[FutureClass, ...]:
    """Load and parse the future-classes CSV. Cached on (path, mtime)."""
    p = csv_path or DEFAULT_CSV
    if not p.exists():
        raise FileNotFoundError(f"Future-classes CSV not found: {p}")
    return _load_classes_cached(str(p.resolve()), p.stat().st_mtime)


# ─────────────────────────────────────────────────────────────────────────────
# Matching
# ─────────────────────────────────────────────────────────────────────────────


def _within_tolerance(query_t: time, cls_t: time, tol_min: int) -> bool:
    qm = query_t.hour * 60 + query_t.minute
    cm = cls_t.hour * 60 + cls_t.minute
    return abs(qm - cm) <= tol_min


def _expand_range(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur = cur + timedelta(days=1)


def _match_single_group(
    pool: Iterable[FutureClass],
    target_dates: set[date] | None,
    studios: set[str] | None,
    disciplines: set[str] | None,
    times: list[time] | None,
    tol: int,
) -> list[FutureClass]:
    """Inner-loop matcher for one resolved set of filters."""
    matches: list[FutureClass] = []
    for cls in pool:
        if target_dates is not None and cls.date not in target_dates:
            continue
        if studios is not None and cls.studio not in studios:
            continue
        if disciplines is not None and cls.discipline not in disciplines:
            continue
        if times is not None:
            if not any(_within_tolerance(t, cls.start_time, tol) for t in times):
                continue
        matches.append(cls)
    return matches


def resolve_request_to_classes(
    query: CoverRequestQuery,
    classes: Iterable[FutureClass] | None = None,
) -> list[FutureClass]:
    """
    Filter the future-classes list against the query.

    Per-group mode (preferred, 2026-05-16+):
      * If ``query.groups`` is non-empty, each CoverRequestGroup is matched
        independently and the results are de-duped (by momence_session_id)
        and unioned.
      * Within a group: a class matches if its date is in the group's dates,
        its studio is in the group's studios, its discipline is in the
        group's disciplines, and its start time is within
        ``time_tolerance_min`` of one of the group's times.
      * Empty fields inside a group mean "any" - so a group with no studios
        listed will match across all studios in its date set.

    Flat / legacy mode:
      * Used when ``query.groups`` is empty.
      * Cross-joins the flat ``dates``, ``times``, ``studios``, ``disciplines``
        sets - which is what created the over-matching the per-group mode
        was introduced to fix. Retained for callers that haven't yet been
        updated to emit groups, and for the date-range branch.
      * If ``query.dates`` is non-empty, a class must fall on one of those dates.
      * Otherwise, if ``date_range_start`` and ``date_range_end`` are set, a
        class must fall in [start, end] inclusive.

    Returns matches sorted by (date, start_time).
    """
    pool = classes if classes is not None else load_future_classes()
    pool_list = list(pool)  # we may iterate multiple times in per-group mode
    tol = query.time_tolerance_min

    # ── Per-group mode ───────────────────────────────────────────────
    if query.groups:
        seen_ids: set[int] = set()
        all_matches: list[FutureClass] = []
        for g in query.groups:
            target_dates = {d for d in g.dates} if g.dates else None
            studios = {s for s in g.studios} if g.studios else None
            disciplines = {d for d in g.disciplines} if g.disciplines else None
            times_list = list(g.times) if g.times else None
            group_matches = _match_single_group(
                pool_list, target_dates, studios, disciplines, times_list, tol
            )
            for m in group_matches:
                if m.momence_session_id in seen_ids:
                    continue
                seen_ids.add(m.momence_session_id)
                all_matches.append(m)
        all_matches.sort(key=lambda c: (c.date, c.start_time))
        return all_matches

    # ── Flat / legacy mode ───────────────────────────────────────────
    target_dates: set[date] | None
    if query.dates:
        target_dates = {d for d in query.dates}
    elif query.date_range_start and query.date_range_end:
        target_dates = set(_expand_range(query.date_range_start, query.date_range_end))
    else:
        target_dates = None  # no date filter

    studios = {s for s in query.studios} if query.studios else None
    disciplines = {d for d in query.disciplines} if query.disciplines else None
    times = list(query.times) if query.times else None

    matches = _match_single_group(
        pool_list, target_dates, studios, disciplines, times, tol
    )
    matches.sort(key=lambda c: (c.date, c.start_time))
    return matches


# ─────────────────────────────────────────────────────────────────────────────
# Pretty-printing helper (for diagnostics, not production)
# ─────────────────────────────────────────────────────────────────────────────


def format_matches(matches: list[FutureClass]) -> str:
    if not matches:
        return "(no matches)"
    lines = [f"{len(matches)} class(es) matched:"]
    for m in matches:
        lines.append(
            f"  {m.date.isoformat()} ({m.weekday}) {m.start_time.strftime('%H:%M')}-"
            f"{m.end_time.strftime('%H:%M')}  "
            f"{m.studio:>10s}  {m.class_name:<20s}  "
            f"id={m.momence_session_id}  teacher={m.teacher!r}"
        )
    return "\n".join(lines)
