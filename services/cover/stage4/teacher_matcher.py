"""
teacher_matcher.py — Stage 4
=============================
Queries the teachers table to find eligible cover candidates for an
approved cover_request.

Matching rules (per the BA plan):
  1.  Grade    — teachers.grades->>'discipline' >= grade_threshold
                 Default threshold = 10 (from system_config)
  2.  Location - request studio in teachers.locations array
  3.  Day      - class day-of-week in teachers.avail_slots keys
  4.  Time     - BOTH the start-time band AND the end-time band must be
                 present in teachers.avail_slots (as 'preferred' or 'emergency').
                 For 1-hour classes near band boundaries this means the
                 teacher needs two adjacent bands marked available.
  5.  Community class — uses trainee_enrollments instead of grades
                 (flagged when discipline_code is None / class is
                 identified as community via class_name_raw).

Results are ranked by grade DESC (most senior first) and capped at
max_candidates (from system_config, default 10).

Usage
-----
    from teacher_matcher import TeacherMatcher
    matcher = TeacherMatcher()
    candidates = matcher.find(cover_request_row)
"""

import sys
from datetime import date, time, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    sb_get, sb_post, get_config_value,
    classify_time_bands, TIME_BANDS
)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_WEEKDAY_MAP = {
    0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu',
    4: 'Fri', 5: 'Sat', 6: 'Sun',
}

_COMMUNITY_KEYWORDS = ['community', 'free class', 'open class']

DEFAULT_DURATION_MIN = 60


# ─────────────────────────────────────────────────────────────────────────────
# Data class
# ─────────────────────────────────────────────────────────────────────────────

class CandidateMatch:
    __slots__ = (
        'teacher_id', 'first_name', 'last_name', 'email',
        'whatsapp_phone', 'contact_preference',
        'matched_grade', 'match_score', 'match_notes',
        'is_community_match',
    )

    def __init__(self, teacher: dict, grade: int, score: int,
                 notes: list, community: bool = False):
        self.teacher_id         = teacher['id']
        self.first_name         = teacher.get('first_name', '')
        self.last_name          = teacher.get('last_name', '')
        self.email              = teacher.get('email')
        self.whatsapp_phone     = teacher.get('whatsapp_phone')
        self.contact_preference = teacher.get('contact_preference', 'whatsapp_channel')
        self.matched_grade      = grade
        self.match_score        = score
        self.match_notes        = '; '.join(notes)
        self.is_community_match = community

    @property
    def full_name(self) -> str:
        return f'{self.first_name} {self.last_name}'.strip()

    def to_db_dict(self, cover_request_id: str,
                   discipline: str) -> dict:
        return {
            'cover_request_id':  cover_request_id,
            'teacher_id':        self.teacher_id,
            'match_score':       self.match_score,
            'matched_grade':     self.matched_grade,
            'matched_discipline': discipline,
        }

    def __repr__(self) -> str:
        return (f'<Candidate {self.full_name} '
                f'grade={self.matched_grade} score={self.match_score}>')


# ─────────────────────────────────────────────────────────────────────────────
# Time band helpers
# ─────────────────────────────────────────────────────────────────────────────

def required_time_bands(class_time: time | None,
                         class_end_time: time | None) -> list[str]:
    """
    Determine which avail_slots time-bands a class spans.

    For a 1-hour class, both the start-time band and the end-time band
    must be covered.  If end_time is unknown, assume DEFAULT_DURATION_MIN.
    """
    if not class_time:
        return []

    if class_end_time:
        end = class_end_time
    else:
        end_dt = datetime.combine(date.today(), class_time) + timedelta(minutes=DEFAULT_DURATION_MIN)
        end = end_dt.time()

    bands = classify_time_bands(
        class_time.hour, class_time.minute,
        end.hour, end.minute
    )
    return bands


def get_slot_state(teacher: dict, day: str, band: str) -> str | None:
    """Return 'preferred', 'emergency', or None for a day+band combination."""
    slots = teacher.get('avail_slots') or {}
    return slots.get(f'{day}|{band}')


def teacher_has_slots(teacher: dict, day: str,
                      req_bands: list[str]) -> str | None:
    """
    Check avail_slots coverage for all required day+band combinations.

    Returns:
      'preferred'  — all required slots are marked preferred
      'emergency'  — all required slots are covered but at least one is emergency
      None         — at least one required slot is absent (teacher cannot cover)

    If req_bands is empty, checks whether the teacher has *any* slot for that
    day (returning None if completely absent, else the best state found).
    """
    slots = teacher.get('avail_slots') or {}
    if not req_bands:
        day_states = [v for k, v in slots.items() if k.startswith(f'{day}|')]
        if not day_states:
            return None
        return 'emergency' if all(s == 'emergency' for s in day_states) else 'preferred'
    states = []
    for band in req_bands:
        state = slots.get(f'{day}|{band}')
        if state is None:
            return None
        states.append(state)
    return 'emergency' if 'emergency' in states else 'preferred'


# ─────────────────────────────────────────────────────────────────────────────
# Grade helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_grade(teacher: dict, discipline: str) -> int:
    """Extract integer grade for a discipline from teachers.grades JSONB."""
    grades = teacher.get('grades') or {}
    try:
        return int(grades.get(discipline, 0) or 0)
    except (ValueError, TypeError):
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# Community class matching
# ─────────────────────────────────────────────────────────────────────────────

def is_community_class(request: dict) -> bool:
    """Return True if this request is for a community class."""
    name_raw = (request.get('class_name_raw') or '').lower()
    return any(kw in name_raw for kw in _COMMUNITY_KEYWORDS)


def find_community_candidates(request: dict, max_candidates: int) -> list[CandidateMatch]:
    """
    For community classes, match via trainee_enrollments.
    The trainee must still pass location and day/time availability checks.
    """
    studio    = request.get('studio')
    class_date_str = request.get('class_date')
    class_time_str = request.get('class_time')
    class_end_str  = request.get('class_end_time')

    class_time = time.fromisoformat(class_time_str) if class_time_str else None
    class_end  = time.fromisoformat(class_end_str)  if class_end_str  else None
    req_bands  = required_time_bands(class_time, class_end)

    req_day = None
    if class_date_str:
        try:
            req_day = _WEEKDAY_MAP[date.fromisoformat(class_date_str).weekday()]
        except (ValueError, KeyError):
            pass

    enrollments = sb_get('trainee_enrollments', params={
        'status': 'eq.active',
        'select': 'teacher_id',
    })
    trainee_ids = {e['teacher_id'] for e in enrollments}

    if not trainee_ids:
        return []

    teachers = sb_get('teachers', params={
        'select': (
            'id,first_name,last_name,email,whatsapp_phone,'
            'contact_preference,locations,avail_slots,grades'
        ),
    })

    candidates = []
    for t in teachers:
        if t['id'] not in trainee_ids:
            continue
        if studio and studio not in (t.get('locations') or []):
            continue
        if req_day:
            slot_result = teacher_has_slots(t, req_day, req_bands)
            if slot_result is None:
                continue

        notes = ['community_class', 'trainee_enrollment']
        if req_day:
            notes.append(f'avail_{req_day}')
        if req_bands:
            notes.append(f'bands={req_bands}')

        candidates.append(CandidateMatch(t, grade=0, score=50, notes=notes, community=True))

    return candidates[:max_candidates]


# ─────────────────────────────────────────────────────────────────────────────
# Standard matching
# ─────────────────────────────────────────────────────────────────────────────

def find_standard_candidates(
    request: dict,
    grade_threshold: int,
    max_candidates: int,
    exclude_teacher_id: str | None = None,
) -> list[CandidateMatch]:
    """
    Find eligible teachers using grade + location + day + time-band filters.

    Composite score (0–100):
      grade        → 50 pts  (scaled: grade / 50 * 50)
      location     → 20 pts  (home_location matches = 20; locations match = 10)
      availability → 30 pts  (preferred slots = 30; emergency slots = 15;
                               no day/time constraint = 10)
    """
    discipline = request.get('discipline_code')
    studio     = request.get('studio')
    class_date_str = request.get('class_date')
    class_time_str = request.get('class_time')
    class_end_str  = request.get('class_end_time')

    class_time = time.fromisoformat(class_time_str) if class_time_str else None
    class_end  = time.fromisoformat(class_end_str)  if class_end_str  else None
    req_bands  = required_time_bands(class_time, class_end)

    req_day = None
    if class_date_str:
        try:
            req_day = _WEEKDAY_MAP[date.fromisoformat(class_date_str).weekday()]
        except (ValueError, KeyError):
            pass

    teachers = sb_get('teachers', params={
        'select': (
            'id,first_name,last_name,email,whatsapp_phone,contact_preference,'
            'home_location,locations,avail_slots,grades'
        ),
    })

    candidates = []

    for t in teachers:
        if exclude_teacher_id and t['id'] == exclude_teacher_id:
            continue

        if not discipline:
            grade = max(
                (int(v or 0) for v in (t.get('grades') or {}).values()),
                default=0
            )
        else:
            grade = get_grade(t, discipline)

        if grade < grade_threshold:
            continue
        if studio and studio not in (t.get('locations') or []):
            continue
        if req_day:
            slot_result = teacher_has_slots(t, req_day, req_bands)
            if slot_result is None:
                continue

        notes  = []
        score  = 0

        grade_pts = min(50, round(grade / 50 * 50))
        score += grade_pts
        notes.append(f'grade={grade}({grade_pts}pts)')

        if studio:
            if t.get('home_location') == studio:
                score += 20; notes.append('home_location(20pts)')
            elif studio in (t.get('locations') or []):
                score += 10; notes.append('locations(10pts)')

        if req_day:
            # Re-evaluate slot state for scoring (filter already confirmed not None)
            slot_result = teacher_has_slots(t, req_day, req_bands)
            if slot_result == 'preferred':
                score += 30; notes.append(f'preferred({req_day}+{req_bands or "any"})(30pts)')
            else:
                score += 15; notes.append(f'emergency({req_day}+{req_bands or "any"})(15pts)')
        else:
            score += 10; notes.append('no_day_constraint(10pts)')

        candidates.append(
            CandidateMatch(t, grade=grade, score=score, notes=notes)
        )

    candidates.sort(key=lambda c: (c.match_score, c.matched_grade), reverse=True)
    return candidates[:max_candidates]


# ─────────────────────────────────────────────────────────────────────────────
# Main matcher class
# ─────────────────────────────────────────────────────────────────────────────

class TeacherMatcher:
    """
    Entry point for Stage 4 teacher matching.
    Call .find(cover_request_row) to get a ranked list of candidates.
    """

    def __init__(self):
        self.grade_threshold = int(
            get_config_value('initial_teacher_grade', '10')
        )
        self.max_candidates = int(
            get_config_value('max_candidates_per_request', '10')
        )

    def find(self, request: dict,
             exclude_teacher_id: str | None = None) -> list[CandidateMatch]:
        """
        Find eligible cover candidates for a cover_request row.
        """
        if is_community_class(request):
            print(f'  Community class detected — using trainee enrollment matching.')
            return find_community_candidates(request, self.max_candidates)

        return find_standard_candidates(
            request,
            grade_threshold=self.grade_threshold,
            max_candidates=self.max_candidates,
            exclude_teacher_id=exclude_teacher_id,
        )

    def save_candidates(self, candidates: list[CandidateMatch],
                        cover_request_id: str,
                        discipline: str,
                        dry_run: bool = False) -> list[str]:
        """
        Persist candidates to cover_candidates table.
        Skips any teacher already stored for this request.
        Returns list of inserted cover_candidate_id values.
        """
        existing = sb_get('cover_candidates', params={
            'cover_request_id': f'eq.{cover_request_id}',
            'select':           'teacher_id',
        })
        existing_ids = {r['teacher_id'] for r in existing}

        inserted_ids = []
        for c in candidates:
            if c.teacher_id in existing_ids:
                print(f'    ↷ {c.full_name}: already a candidate — skipping')
                continue

            payload = c.to_db_dict(cover_request_id, discipline)

            if dry_run:
                print(
                    f'    [DRY RUN] Would add candidate: {c.full_name} '
                    f'score={c.match_score} grade={c.matched_grade}'
                )
                continue

            row = sb_post('cover_candidates', payload)
            cand_id = row[0]['cover_candidate_id'] if row else None
            if cand_id:
                inserted_ids.append(cand_id)
                print(
                    f'    ✓ {c.full_name}: '
                    f'score={c.match_score} grade={c.matched_grade}'
                )

        return inserted_ids


# ─────────────────────────────────────────────────────────────────────────────
# CLI (for testing matching on a specific request)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    ap = argparse.ArgumentParser(description='Test teacher matching for a cover request')
    ap.add_argument('request_id', help='cover_request UUID to test matching on')
    ap.add_argument('--save', action='store_true',
                    help='Save candidates to DB (default: print only)')
    args = ap.parse_args()

    rows = sb_get('cover_requests', params={
        'cover_request_id': f'eq.{args.request_id}',
        'select': (
            'cover_request_id,discipline_code,studio,class_date,'
            'class_time,class_end_time,class_name_raw,'
            'requesting_teacher_id,requesting_teacher_name_raw,'
            'confidence_score,status'
        ),
    })
    if not rows:
        print(f'No cover_request found with id {args.request_id}')
        sys.exit(1)

    req = rows[0]
    print(f'\nMatching for request {args.request_id}')
    print(f'  discipline={req.get("discipline_code")} studio={req.get("studio")}')
    print(f'  date={req.get("class_date")} time={req.get("class_time")}')
    print()

    matcher    = TeacherMatcher()
    candidates = matcher.find(req, exclude_teacher_id=req.get('requesting_teacher_id'))

    print(f'Found {len(candidates)} candidate(s):')
    for i, c in enumerate(candidates, 1):
        print(
            f'  {i}. {c.full_name:30s} '
            f'grade={c.matched_grade:3d}  score={c.match_score:3d}  '
            f'[{c.match_notes}]'
        )

    if args.save and candidates:
        print('\nSaving candidates to DB…')
        matcher.save_candidates(
            candidates, args.request_id,
            req.get('discipline_code', ''), dry_run=False
        )
