"""
momence_crosscheck.py — Stage 3
================================
Cross-checks parsed cover requests against the Ritual Dashboard schedule.

For each cover_request with status 'pending_review' that has no
momence_session_id yet, this module:

  1.  Loads classes from Ritual Dashboard data (dashboard/data/raw/momence_*.json)
  2.  Scores candidate sessions against parsed fields
      (time, studio, discipline, teacher name)
  3.  If a confident match is found:
        • sets  momence_session_id on the cover_request
        • confirms / corrects class_time, class_end_time, studio
        • raises confidence_score if the match confirms the parse
        • clears auto_review_required if combined confidence ≥ threshold
  4.  Appends match rationale to parse_notes throughout

The module does NOT change status — that remains admin's decision.

Usage
-----
    python momence_crosscheck.py              # process all pending requests
    python momence_crosscheck.py --dry-run   # show changes without writing
    python momence_crosscheck.py --id <uuid> # process a single request
"""

import sys
import argparse
import json
from datetime import datetime, date, time, timedelta
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    sb_get,
    sb_patch,
    get_config_value,
    NLP_CONFIDENCE_THRESHOLD,
    DISCIPLINE_PATTERNS,
    STUDIO_MAP,
    classify_time_bands,
)

from dashboard_sessions import load_sessions_for_date


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Minimum score (0–100) for a session to be considered a match
SESSION_MATCH_THRESHOLD = 55

# Maximum time difference (minutes) between parsed time and Momence session start
MAX_TIME_DIFF_MINUTES = 15

# Default class duration if Momence does not provide one
DEFAULT_CLASS_DURATION_MIN = 60


# ─────────────────────────────────────────────────────────────────────────────
# Scoring helpers
# ─────────────────────────────────────────────────────────────────────────────


def _name_similarity(a: str, b: str) -> float:
    """Fuzzy string similarity 0.0–1.0."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _parse_session_time(session: dict) -> time | None:
    """Extract session start time from a Momence session object."""
    for field in ("startsAt", "startTime", "start_time", "startDate", "start"):
        val = session.get(field)
        if val:
            try:
                if "T" in str(val):
                    return datetime.fromisoformat(val.replace("Z", "+00:00")).time()
                return time.fromisoformat(val[:8])
            except (ValueError, AttributeError):
                continue
    return None


def _parse_session_duration(session: dict) -> int:
    """Return session duration in minutes, or DEFAULT_CLASS_DURATION_MIN."""
    for field in (
        "durationInMinutes",
        "duration",
        "durationMinutes",
        "duration_minutes",
    ):
        val = session.get(field)
        if val:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass
    return DEFAULT_CLASS_DURATION_MIN


def _infer_discipline(class_name: str) -> str | None:
    name_lower = (class_name or "").lower()
    for pattern, code in DISCIPLINE_PATTERNS:
        if pattern in name_lower:
            return code
    return None


def _infer_studio(location_name: str) -> str | None:
    loc_lower = (location_name or "").lower()
    for key, val in STUDIO_MAP.items():
        if key in loc_lower:
            return val
    return None


def score_session(session: dict, request: dict) -> tuple[int, list[str]]:
    """
    Score a Momence session against a cover_request.

    Returns (score 0–100, list_of_score_components).
    Components add up to 100:
      time match    → up to 40 pts
      studio match  → up to 25 pts
      discipline    → up to 20 pts
      teacher name  → up to 15 pts
    """
    notes = []
    score = 0

    # ── Time match (40 pts) ──────────────────────────────────────────────────
    req_time = request.get("class_time")  # "HH:MM:SS" string or None
    ses_time = _parse_session_time(session)

    if req_time and ses_time:
        try:
            rt = time.fromisoformat(req_time)
            diff = abs(
                (
                    datetime.combine(date.today(), rt)
                    - datetime.combine(date.today(), ses_time)
                ).total_seconds()
                / 60
            )
            if diff == 0:
                pts = 40
                tag = "exact"
            elif diff <= 5:
                pts = 35
                tag = f"±{int(diff)}min"
            elif diff <= MAX_TIME_DIFF_MINUTES:
                pts = 20
                tag = f"±{int(diff)}min"
            else:
                pts = 0
                tag = f"off by {int(diff)}min"
            score += pts
            notes.append(f"time:{tag}({pts}pts)")
        except ValueError:
            notes.append("time:unparseable(0pts)")
    else:
        notes.append("time:missing(0pts)")

    # ── Studio match (25 pts) ────────────────────────────────────────────────
    req_studio = request.get("studio")
    location = session.get("inPersonLocation") or session.get("location") or {}
    loc_name = location.get("name") if isinstance(location, dict) else str(location)
    ses_studio = _infer_studio(loc_name or "")

    if req_studio and ses_studio:
        if req_studio == ses_studio:
            score += 25
            notes.append("studio:match(25pts)")
        else:
            notes.append(f"studio:mismatch({req_studio}!={ses_studio})(0pts)")
    elif not req_studio:
        if ses_studio:
            score += 10
            notes.append(f"studio:inferred={ses_studio}(10pts)")
        else:
            notes.append("studio:unknown(0pts)")
    else:
        notes.append("studio:session_location_missing(0pts)")

    # ── Discipline match (20 pts) ────────────────────────────────────────────
    req_disc = request.get("discipline_code")
    ses_disc = _infer_discipline(session.get("name") or session.get("title") or "")

    if req_disc and ses_disc:
        if req_disc == ses_disc:
            score += 20
            notes.append("discipline:match(20pts)")
        else:
            notes.append(f"discipline:mismatch({req_disc}!={ses_disc})(0pts)")
    elif not req_disc and ses_disc:
        score += 10
        notes.append(f"discipline:inferred={ses_disc}(10pts)")
    else:
        notes.append("discipline:unknown(0pts)")

    # ── Teacher name match (15 pts) ──────────────────────────────────────────
    req_name = request.get("requesting_teacher_name_raw") or ""
    teacher_obj = session.get("teacher") or session.get("instructor") or {}
    t_first = teacher_obj.get("firstName") or teacher_obj.get("first_name") or ""
    t_last = teacher_obj.get("lastName") or teacher_obj.get("last_name") or ""
    ses_name = f"{t_first} {t_last}".strip()

    if req_name and ses_name:
        sim = _name_similarity(req_name, ses_name)
        pts = round(15 * sim)
        score += pts
        notes.append(f"teacher:{sim:.0%}sim({pts}pts)")
    else:
        notes.append("teacher:name_missing(0pts)")

    return score, notes


# ─────────────────────────────────────────────────────────────────────────────
# Momence session fetching
# ─────────────────────────────────────────────────────────────────────────────


def fetch_sessions_for_date(target_date: date) -> list[dict]:
    """
    Load sessions from Ritual Dashboard for target_date ± 1 day.
    """
    return load_sessions_for_date(target_date, lookback_days=1)


def filter_to_target_date(sessions: list, target_date: date) -> list:
    """Keep only sessions whose start date matches target_date."""
    result = []
    print(f"  [DEBUG] Filtering {len(sessions)} sessions for date {target_date}")
    date_counts = {}
    for s in sessions:
        if not isinstance(s, dict):
            continue
        ses_time = _parse_session_time(s)
        if ses_time is None:
            for field in ("startDate", "start_date", "date"):
                val = s.get(field)
                if val:
                    try:
                        session_date = date.fromisoformat(str(val)[:10])
                        date_counts[session_date] = date_counts.get(session_date, 0) + 1
                        if session_date == target_date:
                            result.append(s)
                    except ValueError:
                        pass
                    break
        else:
            for field in ("startsAt", "startTime", "start_time", "startDate", "start"):
                val = s.get(field)
                if val and "T" in str(val):
                    try:
                        ses_date = datetime.fromisoformat(
                            val.replace("Z", "+00:00")
                        ).date()
                        date_counts[ses_date] = date_counts.get(ses_date, 0) + 1
                        if ses_date == target_date:
                            result.append(s)
                    except ValueError:
                        pass
                    break
    print(f"  [DEBUG] Sessions by date: {dict(sorted(date_counts.items())[:5])}...")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Update builder
# ─────────────────────────────────────────────────────────────────────────────


def build_update(
    request: dict, best_session: dict, score: int, score_notes: list
) -> dict:
    """
    Build the Supabase PATCH payload to apply the Momence cross-check result.
    """
    session_id = best_session.get("id") or best_session.get("sessionId")
    ses_time = _parse_session_time(best_session)
    duration = _parse_session_duration(best_session)

    end_time = None
    if ses_time:
        end_dt = datetime.combine(date.today(), ses_time) + timedelta(minutes=duration)
        end_time = end_dt.time().isoformat()

    location = (
        best_session.get("inPersonLocation") or best_session.get("location") or {}
    )
    loc_name = location.get("name") if isinstance(location, dict) else str(location)
    ses_studio = _infer_studio(loc_name or "")

    ses_disc = _infer_discipline(
        best_session.get("name") or best_session.get("title") or ""
    )

    existing_conf = float(request.get("confidence_score") or 0.0)
    if score >= 80:
        new_conf = min(1.0, existing_conf + 0.20)
    elif score >= SESSION_MATCH_THRESHOLD:
        new_conf = min(1.0, existing_conf + 0.10)
    else:
        new_conf = existing_conf

    threshold = float(
        get_config_value("nlp_confidence_threshold", str(NLP_CONFIDENCE_THRESHOLD))
        or str(NLP_CONFIDENCE_THRESHOLD)
    )
    auto_review = new_conf < threshold

    notes = (request.get("parse_notes") or "") + (
        f' | Momence match: score={score} [{"; ".join(score_notes)}]'
        f" session_id={session_id}"
        f' class={best_session.get("name") or best_session.get("title")}'
        f" duration={duration}min"
    )

    update: dict = {
        "momence_session_id": int(session_id) if session_id else None,
        "confidence_score": round(new_conf, 3),
        "auto_review_required": auto_review,
        "parse_notes": notes.strip(),
    }

    if ses_time:
        update["class_time"] = ses_time.isoformat()
        if end_time:
            update["class_end_time"] = end_time
    if ses_studio and not request.get("studio"):
        update["studio"] = ses_studio
    if ses_disc and not request.get("discipline_code"):
        update["discipline_code"] = ses_disc

    if not request.get("class_name_raw"):
        update["class_name_raw"] = (
            best_session.get("title") or best_session.get("name") or ""
        )

    return update


def build_no_match_update(request: dict, sessions_checked: int) -> dict:
    """Append a no-match note to parse_notes; leave status unchanged."""
    notes = (request.get("parse_notes") or "") + (
        f" | Momence cross-check: no match found"
        f' (checked {sessions_checked} sessions on {request.get("class_date")})'
        f" — manual admin review required."
    )
    return {
        "auto_review_required": True,
        "parse_notes": notes.strip(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Core processor
# ─────────────────────────────────────────────────────────────────────────────


def process_request(request: dict, dry_run: bool = False) -> str:
    """
    Cross-check a single cover_request against dashboard sessions.
    Returns: 'matched' | 'no_match' | 'no_date' | 'already_linked'
    """
    req_id = request["cover_request_id"]

    if request.get("momence_session_id"):
        print(
            f'  Already linked to session {request["momence_session_id"]} — skipping.'
        )
        return "already_linked"

    class_date_str = request.get("class_date")
    if not class_date_str:
        print(f"  No class_date — cannot cross-check. Manual review required.")
        return "no_date"

    try:
        target_date = date.fromisoformat(class_date_str)
    except ValueError:
        print(f'  Invalid class_date "{class_date_str}" — skipping.')
        return "no_date"

    print(f"  Fetching dashboard sessions for {target_date}…")
    all_sessions = fetch_sessions_for_date(target_date)
    print(f"  [DEBUG] Total sessions fetched: {len(all_sessions)}")
    day_sessions = filter_to_target_date(all_sessions, target_date)
    print(f"  -> {len(day_sessions)} session(s) on {target_date}")
    if day_sessions and len(day_sessions) <= 3:
        print(f"  [DEBUG] Sessions on target date:")
        for i, s in enumerate(day_sessions[:3]):
            print(
                f"    [{i}] {s.get('name', '?')} @ {s.get('startsAt', s.get('start_time', '?'))}"
            )

    if not day_sessions:
        update = build_no_match_update(request, 0)
        if not dry_run:
            sb_patch("cover_requests", update, {"cover_request_id": f"eq.{req_id}"})
        print(f"  No sessions on {target_date} in Momence.")
        return "no_match"

    scored = []
    for s in day_sessions:
        sc, notes = score_session(s, request)
        scored.append((sc, notes, s))
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score, best_notes, best_session = scored[0]
    print(
        f"  Best match: score={best_score} — "
        f'{best_session.get("title") or best_session.get("name")} '
        f'[{"; ".join(best_notes)}]'
    )
    print(f"  [DEBUG] Best session ID: {best_session.get('id')}")
    print(f"  [DEBUG] Best session details:")
    for key in [
        "id",
        "name",
        "title",
        "startsAt",
        "endsAt",
        "durationInMinutes",
        "teacher",
        "inPersonLocation",
    ]:
        val = best_session.get(key)
        if val:
            print(f"    {key}: {val}")

    if best_score >= SESSION_MATCH_THRESHOLD:
        update = build_update(request, best_session, best_score, best_notes)
        print(f"  [DEBUG] Update payload:")
        for key, val in update.items():
            if key == "parse_notes":
                print(f"    {key}: {val[:100]}...")
            else:
                print(f"    {key}: {val}")
        if not dry_run:
            result = sb_patch(
                "cover_requests", update, {"cover_request_id": f"eq.{req_id}"}
            )
            print(
                f"  OK Linked to Momence session " f'{update.get("momence_session_id")}'
            )
            print(f"  [DEBUG] Supabase update result: {len(result)} rows updated")
        else:
            print(f"  [DRY RUN] Would update: {list(update.keys())}")
        return "matched"
    else:
        print(
            f"  Score {best_score} < threshold {SESSION_MATCH_THRESHOLD} "
            f"— no confident match."
        )
        update = build_no_match_update(request, len(day_sessions))
        if not dry_run:
            sb_patch("cover_requests", update, {"cover_request_id": f"eq.{req_id}"})
        return "no_match"


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def run(request_id: str | None = None, dry_run: bool = False) -> None:
    mode = "[DRY RUN] " if dry_run else ""
    print(f'\n{"="*60}')
    print(f"{mode}Momence Cross-Check — Stage 3")
    print(f'{"="*60}\n')

    params = {
        "select": (
            "cover_request_id,class_date,class_time,studio,"
            "discipline_code,requesting_teacher_name_raw,"
            "momence_session_id,confidence_score,parse_notes,"
            "class_name_raw,auto_review_required"
        ),
        "status": "eq.pending_review",
        "order": "created_at",
    }
    if request_id:
        params.pop("status")
        params["cover_request_id"] = f"eq.{request_id}"

    requests_list = sb_get("cover_requests", params=params)
    print(f"Requests to cross-check: {len(requests_list)}")

    if not requests_list:
        print("Nothing to process.")
        return

    print("\nLoading Dashboard data…")

    counts = {"matched": 0, "no_match": 0, "no_date": 0, "already_linked": 0}

    for i, req in enumerate(requests_list, 1):
        req_id = req["cover_request_id"]
        print(f"\n[{i}/{len(requests_list)}] Request {req_id}")
        print(
            f'  date={req.get("class_date")} time={req.get("class_time")} '
            f'studio={req.get("studio")} discipline={req.get("discipline_code")}'
        )
        print(f'  teacher={req.get("requesting_teacher_name_raw")}')

        outcome = process_request(req, dry_run=dry_run)
        counts[outcome] = counts.get(outcome, 0) + 1

    print(f'\n{"="*60}')
    print(f"Cross-check complete:")
    print(f'  Matched:        {counts["matched"]}')
    print(f'  No match:       {counts["no_match"]}')
    print(f'  No date:        {counts["no_date"]}')
    print(f'  Already linked: {counts["already_linked"]}')


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Cross-check cover requests against Momence"
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without writing to Supabase",
    )
    ap.add_argument(
        "--id", metavar="UUID", help="Process a single cover_request by UUID"
    )
    args = ap.parse_args()
    run(request_id=args.id, dry_run=args.dry_run)
