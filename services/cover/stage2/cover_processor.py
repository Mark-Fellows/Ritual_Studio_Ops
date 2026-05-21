"""
cover_processor.py -- Stage 2  (main entry point)
Orchestrates: WhatsApp read -> NLP parse -> deduplicate -> insert to Supabase.
Run 3-4 times per day via Windows Task Scheduler.

Usage
-----
    python cover_processor.py                   # normal run (attach mode)
    python cover_processor.py --launch          # launch Chrome
    python cover_processor.py --hours 8         # longer lookback
    python cover_processor.py --dry-run         # parse but do not write to DB
    python cover_processor.py --test-parse      # test NLP on a single message
"""

import sys
import argparse
import hashlib
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

# Force stdout/stderr to UTF-8 with replacement on un-encodable chars.
# Reason: nlp_parser.py prints a box-drawing glyph (U+2500) when a
# message is classified as "not cover-related". On Windows with stdout
# redirected, Python defaults to cp1252 and crashes on that character
# (UnicodeEncodeError). PYTHONIOENCODING=utf-8 fixes this *only* when
# correctly exported as a process environment variable - which happens
# from cmd / run_monitor.bat but NOT from PowerShell where `set X=...`
# is the local-variable command. Reconfiguring here makes the script
# self-defensive: it works the same regardless of launcher.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    # Python < 3.7 or non-reconfigurable streams (e.g. IDE consoles)
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "stage3"))

from config import (
    sb_get,
    sb_post,
    sb_patch,
    WHATSAPP_LOOKBACK_HOURS,
    NLP_CONFIDENCE_THRESHOLD,
)
from whatsapp_monitor import WhatsAppMonitor, update_run_requests_found
from nlp_parser import NLPParser, GeminiNLPParser, parse_messages, parse_messages_dual

# Stage 3 - resolve a parsed request into the concrete list of Momence
# classes. Imported lazily-tolerant: if the CSV is unavailable, resolution
# is skipped and the cover_request is still inserted (just without
# momence_session_ids / resolved_classes).
try:
    from resolve_classes import (
        CoverRequestGroup,
        CoverRequestQuery,
        FutureClass,
        load_future_classes,
        resolve_request_to_classes,
    )
    _RESOLVER_AVAILABLE = True
except Exception as _resolver_import_err:  # pragma: no cover - defensive
    print(f"[WARN] Stage 3 resolver unavailable: {_resolver_import_err}")
    _RESOLVER_AVAILABLE = False


def clear_cover_requests(
    older_than_days: int | None = None, confirm: bool = True
) -> bool:
    """
    Clear entries from cover_requests table.

    Parameters
    ----------
    older_than_days : int | None
        If specified, only clear entries older than N days.
        If None, clear ALL entries (use with caution).
    confirm : bool
        If True, prompt for confirmation before deletion.

    Returns
    -------
    bool
        True if cleared successfully, False if cancelled.
    """
    try:
        if older_than_days:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
            rows = sb_get(
                "cover_requests",
                params={
                    "select": "cover_request_id,created_at,requesting_teacher_name_raw,message_timestamp",
                    "created_at": f"lt.{cutoff}",
                },
            )
            msg = f"Clear {len(rows)} entries older than {older_than_days} days?"
        else:
            rows = sb_get("cover_requests", params={"select": "cover_request_id"})
            msg = f"Clear ALL {len(rows)} entries from cover_requests table?\n\n⚠️  THIS CANNOT BE UNDONE."

        if not rows:
            print("No entries to clear.")
            return False

        print(f"\n{msg}")
        if confirm:
            response = input('Type "yes" to confirm: ').strip().lower()
            if response != "yes":
                print("Cancelled.")
                return False

        # Delete via Supabase (RLS permitting)
        # Note: Supabase doesn't have a direct bulk delete via PostgREST,
        # so we delete by cover_request_id in batches
        deleted_count = 0
        for i, row in enumerate(rows, 1):
            try:
                # This requires RLS policy or service role key
                # For now, show what would be deleted
                print(
                    f'  [{i}/{len(rows)}] {row.get("cover_request_id")} - {row.get("requesting_teacher_name_raw")}'
                )
                deleted_count += 1
            except Exception as e:
                print(f'  Error deleting {row.get("cover_request_id")}: {e}')

        print(f"\n✓ Ready to delete {deleted_count} entries.")
        print(
            "\n⚠️  NOTE: Direct deletion requires Supabase service role key or RLS bypass."
        )
        print("   For now, you can run this SQL in Supabase dashboard:")

        if older_than_days:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
            print(f"\n   DELETE FROM cover_requests WHERE created_at < '{cutoff}';")
        else:
            print(f"\n   DELETE FROM cover_requests;")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


def _message_fingerprint(sender: str, timestamp: datetime | None, text: str) -> str:
    if timestamp:
        # Normalise to UTC so AEST-aware scraper timestamps and UTC DB values
        # produce the same hour bucket (avoids 10-hour offset mismatches).
        if timestamp.tzinfo is not None:
            ts_utc = timestamp.astimezone(timezone.utc)
        else:
            ts_utc = timestamp  # naive — treated as UTC, consistent with Postgres
        hour_bucket = ts_utc.strftime("%Y%m%d%H")
    else:
        hour_bucket = ""
    raw = f"{sender.lower()}|{hour_bucket}|{text[:120].strip()}"
    return hashlib.sha1(raw.encode()).hexdigest()


def load_recent_fingerprints(lookback_hours: int = 48) -> set[str]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
    rows = sb_get(
        "cover_requests",
        params={
            "select": "requesting_teacher_name_raw,message_timestamp,raw_message",
            "created_at": f"gte.{cutoff}",
        },
    )
    fps = set()
    for r in rows:
        ts = (
            datetime.fromisoformat(r["message_timestamp"])
            if r.get("message_timestamp")
            else None
        )
        fps.add(
            _message_fingerprint(
                r.get("requesting_teacher_name_raw") or "",
                ts,
                r.get("raw_message") or "",
            )
        )
    return fps


def load_recent_wa_fingerprints(lookback_hours: int = 48) -> set[str]:
    """Load deduplication fingerprints from the whatsapp_messages table."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
    rows = sb_get(
        "whatsapp_messages",
        params={
            "select": "teacher_sender_name,message_timestamp,raw_whatsapp_text",
            "created_at": f"gte.{cutoff}",
        },
    )
    fps = set()
    for r in rows:
        ts = (
            datetime.fromisoformat(r["message_timestamp"])
            if r.get("message_timestamp")
            else None
        )
        fps.add(
            _message_fingerprint(
                r.get("teacher_sender_name") or "",
                ts,
                r.get("raw_whatsapp_text") or "",
            )
        )
    return fps


def resolve_teacher_id(name_raw: str | None) -> str | None:
    if not name_raw:
        return None
    name_lower = name_raw.strip().lower()
    parts = name_lower.split()
    teachers = sb_get("teachers", params={"select": "id,first_name,last_name"})
    for t in teachers:
        if f'{t["first_name"]} {t["last_name"]}'.lower() == name_lower:
            return t["id"]
    if parts:
        m = [t for t in teachers if t["first_name"].lower() == parts[0]]
        if len(m) == 1:
            return m[0]["id"]
    if len(parts) > 1:
        m = [t for t in teachers if t["last_name"].lower() == parts[-1]]
        if len(m) == 1:
            return m[0]["id"]
    return None



# Columns that exist in the cover_requests table (from 01_cover_schema.sql).
# to_db_dict() now also emits newer fields (coverage_type, class_times, etc.)
# that only exist in whatsapp_messages — strip those before posting here.
_COVER_REQUESTS_COLUMNS = frozenset({
    "whatsapp_channel_id",
    "raw_message",
    "message_timestamp",
    "requesting_teacher_id",
    "requesting_teacher_name_raw",
    "class_date",
    "class_time",
    "class_end_time",
    "studio",
    "discipline_code",
    "class_name_raw",
    "confidence_score",
    "auto_review_required",
    "parse_notes",
    "status",
    "admin_notes",
    "reviewed_by",
    "reviewed_at",
    # Added 2026-04-24 — requires MIGRATION-coverage-type-cover-requests.sql
    "coverage_type",
    "coverage_type_confidence",
    # Added 2026-05-08 — requires MIGRATION-class-dates-and-resolved-classes-2026-05-07.sql
    "momence_session_ids",
    "resolved_classes",
    "classes_resolved_at",
})


def _resolve_classes_for_result(result) -> list:
    """
    Resolve a parsed request to the concrete list of Momence classes
    described in data/momence_classes_future.csv.

    Returns an empty list if the resolver is unavailable, the message
    isn't a request, or there's not enough structured data to query.
    """
    if not _RESOLVER_AVAILABLE:
        return []
    if getattr(result, "message_type", None) != "request":
        return []

    dates = list(result.class_dates or [])
    if not dates and result.class_date:
        dates = [result.class_date]
    if not dates:
        return []  # no specific dates to resolve against

    times = list(result.class_times or [])
    if not times and result.class_time:
        times = [result.class_time]

    studios = list(result.studios or [])
    if not studios and result.studio:
        studios = [result.studio]

    disciplines = list(result.discipline_codes or [])
    if not disciplines and result.discipline_code:
        disciplines = [result.discipline_code]

    # Convert NLP-parser cover_groups (list of dicts of ISO strings) into
    # CoverRequestGroup objects with parsed date/time values. Added 2026-05-16
    # to fix the cross-join over-matching that returned eg 10 classes for
    # Leah's clearly-stated 4-class request. When groups are present the
    # resolver matches each group independently (correct); when absent it
    # falls back to the legacy flat-list cross-join (still wrong, but
    # required for back-compat with un-grouped messages).
    groups: list[CoverRequestGroup] = []
    for g in (getattr(result, "cover_groups", None) or []):
        try:
            g_dates = []
            for d_iso in g.get("dates", []):
                try: g_dates.append(date.fromisoformat(d_iso))
                except (ValueError, TypeError): pass
            g_times = []
            for t_iso in g.get("times", []):
                try:
                    # Strip leading/trailing whitespace; accept either "HH:MM"
                    # or "HH:MM:SS" (Claude has been inconsistent).
                    t_clean = (t_iso or "").strip()
                    if len(t_clean) == 5:
                        t_clean = t_clean + ":00"
                    from datetime import time as _time
                    g_times.append(_time.fromisoformat(t_clean))
                except (ValueError, TypeError): pass
            groups.append(CoverRequestGroup(
                dates=g_dates,
                times=g_times,
                studios=list(g.get("studios") or []),
                disciplines=list(g.get("disciplines") or []),
            ))
        except Exception as e:  # pragma: no cover - defensive
            print(f"    [resolver] skipping malformed cover_group: {e}")

    try:
        query = CoverRequestQuery(
            groups=groups,             # preferred per-clause matching
            dates=dates,               # legacy fallback when groups is empty
            times=times,
            studios=studios,
            disciplines=disciplines,
        )
        return resolve_request_to_classes(query)
    except FileNotFoundError as e:
        print(f"    [resolver] CSV not found: {e}")
        return []
    except Exception as e:  # pragma: no cover - defensive
        print(f"    [resolver] Unexpected error: {e}")
        return []


def insert_whatsapp_message(msg, result, existing_fps: set, dry_run: bool) -> bool:
    """
    Insert a cover REQUEST into the cover_requests table.
    Offers and rejections are skipped here (only requests are stored in that table).

    Parameters
    ----------
    msg : ChannelMessage
        The WhatsApp message.
    result : ParseResult
        The parsed result (with message_type and appropriate fields).
    existing_fps : set
        Set of existing fingerprints for deduplication.
    dry_run : bool
        If True, don't actually insert; just print what would be inserted.

    Returns
    -------
    bool
        True if inserted (or would be inserted), False if duplicate, skipped, or error.
    """
    # cover_requests only stores requests, not offers/rejections
    if result.message_type != "request":
        return False

    teacher_name = result.teacher_name
    fp = _message_fingerprint(teacher_name or msg.sender, msg.timestamp, msg.text)
    if fp in existing_fps:
        print("    -> Duplicate - already stored, skipping.")
        return False

    channel_db_id = getattr(msg, "_channel_db_id", None)
    full_payload = result.to_db_dict(
        channel_db_id=channel_db_id,
        raw_message=msg.text,
        message_timestamp=msg.timestamp,
    )

    # Strip any columns that don't exist in cover_requests
    payload = {k: v for k, v in full_payload.items() if k in _COVER_REQUESTS_COLUMNS}

    # Resolve teacher ID
    if teacher_name:
        teacher_id = resolve_teacher_id(teacher_name)
        if teacher_id:
            payload["requesting_teacher_id"] = teacher_id

    # Stage 3 - resolve to concrete Momence classes from
    # data/momence_classes_future.csv. We store the durable Class Numbers
    # plus a snapshot of each row's metadata so later re-resolutions can
    # detect drift (TBA teacher updates, ±15-30 min time alterations,
    # class-type changes).
    matched = _resolve_classes_for_result(result)
    if matched:
        # Store as native Python lists — requests will serialise these as
        # JSON arrays. Do NOT use json.dumps() here: that would create a
        # JSON *string* in the JSONB column instead of a JSON array, causing
        # Array.isArray() to return false in the dashboard.
        payload["momence_session_ids"] = [m.momence_session_id for m in matched]
        payload["resolved_classes"]    = [m.to_snapshot_dict()  for m in matched]
        payload["classes_resolved_at"] = datetime.now(timezone.utc).isoformat()
        print(f"    [resolver] matched {len(matched)} Momence class(es)")
    else:
        print("    [resolver] no Momence matches (or insufficient query data)")

    if dry_run:
        print(f"    [DRY RUN] Would insert REQUEST to cover_requests:")
        for k, v in payload.items():
            if v is not None:
                print(f"      {k}: {v}")
        existing_fps.add(fp)
        return True

    try:
        rows = sb_post("cover_requests", payload)
        msg_id = rows[0]["cover_request_id"] if rows else "?"
        print(f"    ok Inserted REQUEST → cover_requests {msg_id}")
        existing_fps.add(fp)
        # Phase 2 — semantic dedup. Failure is non-fatal.
        if matched and msg_id and msg_id != "?":
            try:
                _check_and_link_duplicate(
                    new_id=msg_id,
                    teacher_id=payload.get("requesting_teacher_id"),
                    teacher_name_raw=teacher_name,
                    new_session_ids=[m.momence_session_id for m in matched],
                    new_message_timestamp=msg.timestamp,
                )
            except Exception as e:
                print(f"    [dedup] check failed (non-fatal): {e}")
        return True
    except Exception as e:
        print(f"    FAILED cover_requests insert: {e}")
        return False


def insert_to_whatsapp_messages_table(
    msg, result, existing_wa_fps: set, dry_run: bool
) -> bool:
    """
    Insert a WhatsApp message into the whatsapp_messages table.

    Uses the correct column names for that table:
      channel_id, raw_whatsapp_text, created_at, teacher_sender_name.

    All cover-related message types (request, offer, rejection, other)
    are written here.

    Parameters
    ----------
    msg : ChannelMessage
        The raw WhatsApp message.
    result : ParseResult
        NLP parse result.
    existing_wa_fps : set
        Fingerprints already present in whatsapp_messages (for dedup).
    dry_run : bool
        If True, print what would be inserted without writing to DB.

    Returns
    -------
    bool
        True if inserted (or would be in dry-run), False if dup or error.
    """
    # The actual author of this WhatsApp message — always msg.sender.
    # msg.original_sender is the *quoted* person (who is being replied to),
    # not the person who sent this message.  The is_quoted_reply flag and
    # quoted_reply_to fields carry that context separately.
    sender = msg.sender or ""

    fp = _message_fingerprint(sender, msg.timestamp, msg.text)
    if fp in existing_wa_fps:
        print("    -> WA dup - already in whatsapp_messages, skipping.")
        return False

    channel_id = getattr(msg, "_channel_db_id", None)
    if not channel_id:
        print(
            f"    SKIP whatsapp_messages — msg._channel_db_id is None "
            f"(channel not found in DB for '{msg.channel}'). Cannot satisfy NOT NULL."
        )
        return False

    _VALID_COVERAGE_TYPES = {"temporary", "permanent", "both"}
    coverage_type_value = result.coverage_type or "both"
    if coverage_type_value not in _VALID_COVERAGE_TYPES:
        coverage_type_value = "both"

    payload: dict = {
        "channel_id": channel_id,
        "raw_whatsapp_text": msg.text,
        "teacher_sender_name": sender,
        "is_quoted_reply": bool(getattr(msg, "is_reply", False)),
        "quoted_reply_to": getattr(msg, "original_sender", None),
        "message_type": result.message_type,
        "confidence_score": round(result.confidence_score, 3),
        "parse_notes": result.parse_notes,
        "coverage_type": coverage_type_value,
        "coverage_type_confidence": round(result.coverage_type_confidence, 2),
    }
    # Store the WhatsApp message timestamp as created_at (overrides DB default).
    # Omit entirely if None so the DB default (now()) applies instead.
    if msg.timestamp:
        payload["message_timestamp"] = msg.timestamp.isoformat()

    if result.message_type == "request":
        payload["status"] = "pending_review"
        payload["requesting_teacher_name_raw"] = result.teacher_name
        if result.class_date:
            payload["class_date"] = result.class_date.isoformat()
        if result.class_times:
            payload["class_times"] = [t.isoformat() for t in result.class_times]
        if result.class_dates:
            payload["class_dates"] = [d.isoformat() for d in result.class_dates]
        if result.studios:
            payload["studios"] = result.studios
        if result.discipline_codes:
            payload["discipline_codes"] = result.discipline_codes
        if result.estimated_class_count is not None:
            payload["estimated_class_count"] = str(result.estimated_class_count)
        teacher_id = resolve_teacher_id(result.teacher_name)
        if teacher_id:
            payload["requesting_teacher_id"] = teacher_id

    elif result.message_type == "offer":
        payload["status"] = "offer_pending"
        payload["offering_teacher_name_raw"] = result.offering_teacher_name
        if result.offered_dates:
            payload["offered_dates"] = [d.isoformat() for d in result.offered_dates]
        if result.offered_times:
            payload["offered_times"] = [t.isoformat() for t in result.offered_times]
        if result.offered_studios:
            payload["offered_studios"] = result.offered_studios
        if result.offered_disciplines:
            payload["offered_disciplines"] = result.offered_disciplines
        if result.can_cover_count is not None:
            payload["can_cover_count"] = result.can_cover_count
        teacher_id = resolve_teacher_id(result.offering_teacher_name)
        if teacher_id:
            payload["offering_teacher_id"] = teacher_id

    elif result.message_type == "rejection":
        payload["status"] = "rejection"
        payload["declining_teacher_name_raw"] = result.declining_teacher_name
        if result.declining_for_whom:
            payload["declining_for_whom"] = result.declining_for_whom
        if result.rejection_reason:
            payload["rejection_reason"] = result.rejection_reason
        teacher_id = resolve_teacher_id(result.declining_teacher_name)
        if teacher_id:
            payload["declining_teacher_id"] = teacher_id

    else:
        # "other" — cover-related but not fully classifiable
        payload["status"] = "pending_review"

    # Dual-model metadata (populated by parse_messages_dual; None in single-model mode)
    if result.nlp_claude_type is not None:
        payload["nlp_claude_type"] = result.nlp_claude_type
    if result.nlp_gemini_type is not None:
        payload["nlp_gemini_type"] = result.nlp_gemini_type
    if result.nlp_disparity_score is not None:
        payload["nlp_disparity_score"] = result.nlp_disparity_score
    payload["nlp_primary_source"] = result.nlp_primary_source

    if dry_run:
        print(f"    [DRY RUN WA] Would insert {result.message_type} to whatsapp_messages:")
        for k, v in payload.items():
            if v is not None:
                print(f"      {k}: {v}")
        existing_wa_fps.add(fp)
        return True

    try:
        rows = sb_post("whatsapp_messages", payload)
        wa_id = rows[0]["whatsapp_message_id"] if rows else "?"
        print(f"    ok WA Inserted {result.message_type.upper()} → whatsapp_messages {wa_id}")
        existing_wa_fps.add(fp)
        return True
    except Exception as e:
        print(f"    FAILED whatsapp_messages insert: {e}")
        return False



# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — semantic dedup using momence_session_ids overlap.
# Trigger threshold + lookback are documented in
# MIGRATION-phase2-dedup-2026-05-09.sql and PHASE-2-DEDUP-DESIGN.md.
# ─────────────────────────────────────────────────────────────────────────────

DEDUP_OVERLAP_THRESHOLD = 0.70
DEDUP_LOOKBACK_DAYS = 90
_DEDUP_OPEN_STATUSES = (
    "pending_review", "in_progress", "approved", "partially_filled",
)


def _overlap_coefficient(a, b) -> float:
    sa, sb = set(a or []), set(b or [])
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def _check_and_link_duplicate(
    new_id: str,
    teacher_id: str | None,
    teacher_name_raw: str | None,
    new_session_ids: list,
    new_message_timestamp: datetime | None,
) -> None:
    """
    Look at OPEN cover_requests from the same teacher in the recent past,
    score them by overlap coefficient against the new row's session IDs,
    and if any beats DEDUP_OVERLAP_THRESHOLD, mark the new row as
    duplicate_of the best match. Excludes the new row itself, and never
    re-links to a row that is already a duplicate.
    """
    if not new_session_ids:
        return

    cutoff = (datetime.now(timezone.utc) - timedelta(days=DEDUP_LOOKBACK_DAYS)).isoformat()
    base_params = {
        "select": (
            "cover_request_id,requesting_teacher_id,requesting_teacher_name_raw,"
            "momence_session_ids,reminder_count,status,message_timestamp"
        ),
        "status": f"in.({','.join(_DEDUP_OPEN_STATUSES)})",
        "message_timestamp": f"gte.{cutoff}",
        "order": "message_timestamp.asc",
    }
    # Candidate pool = UNION of (rows with same teacher_id) and (rows with
    # same teacher_name_raw, case-insensitive). Some legacy rows have only
    # the name resolved and not the id (or vice versa) so a single filter
    # would miss them. We dedupe the union by cover_request_id.
    if not teacher_id and not teacher_name_raw:
        return
    queries: list[dict] = []
    if teacher_id:
        queries.append({"requesting_teacher_id": f"eq.{teacher_id}"})
    if teacher_name_raw:
        queries.append({"requesting_teacher_name_raw": f"ilike.{teacher_name_raw}"})

    candidates: list[dict] = []
    seen_ids: set[str] = set()
    for q in queries:
        params = {**base_params, **q}
        try:
            rows = sb_get("cover_requests", params=params)
        except Exception as e:
            print(f"    [dedup] candidate fetch failed ({list(q.keys())[0]}): {e}")
            continue
        for r in rows:
            rid = r.get("cover_request_id")
            if rid and rid not in seen_ids:
                candidates.append(r)
                seen_ids.add(rid)

    best_id, best_score, best_existing_count = None, 0.0, 0
    new_set = set(new_session_ids)
    for c in candidates:
        if c.get("cover_request_id") == new_id:
            continue
        if c.get("status") == "duplicate_of":
            continue
        existing = c.get("momence_session_ids") or []
        if not existing:
            continue
        score = _overlap_coefficient(new_set, existing)
        if score > best_score:
            best_id = c["cover_request_id"]
            best_score = score
            best_existing_count = c.get("reminder_count", 0) or 0

    if not best_id or best_score < DEDUP_OVERLAP_THRESHOLD:
        return

    try:
        sb_patch(
            "cover_requests",
            {"status": "duplicate_of", "parent_cover_request_id": best_id},
            match_params={"cover_request_id": f"eq.{new_id}"},
        )
        bump_payload: dict = {"reminder_count": best_existing_count + 1}
        if new_message_timestamp:
            bump_payload["last_reminder_at"] = new_message_timestamp.isoformat()
        sb_patch(
            "cover_requests",
            bump_payload,
            match_params={"cover_request_id": f"eq.{best_id}"},
        )
        print(
            f"    [dedup] linked to parent {best_id}  "
            f"(overlap={best_score:.2f}, parent reminder_count→{best_existing_count + 1})"
        )
    except Exception as e:
        print(f"    [dedup] PATCH failed: {e}")


def run(
    lookback_hours: int = WHATSAPP_LOOKBACK_HOURS,
    launch_mode: bool = False,
    dry_run: bool = False,
    all_messages: bool = False,
) -> None:
    print(f'\n{"="*60}')
    print(f'Cover Processor  {"[DRY RUN] " if dry_run else ""}{"[ALL MESSAGES] " if all_messages else ""}')
    print(f"Lookback: {lookback_hours}h | NLP threshold: {NLP_CONFIDENCE_THRESHOLD}")
    print(f'{"="*60}\n')

    print("STEP 1 - Reading WhatsApp channels...")
    monitor = WhatsAppMonitor(lookback_hours=lookback_hours, launch_mode=launch_mode)
    messages = monitor.run()
    if not messages:
        print("\nNo messages retrieved. Exiting.")
        return

    print(f"\nSTEP 2 - Parsing {len(messages)} messages with NLP (dual: Claude + Gemini)...")
    # Attempt to initialise both parsers. If Gemini credentials are missing
    # or the package is not installed, fall back to Claude-only single-parse.
    _gemini_parser = None
    try:
        _gemini_parser = GeminiNLPParser()
    except Exception as _gemini_err:
        print(f"  [WARN] Gemini parser unavailable ({_gemini_err}); falling back to Claude-only.")

    if _gemini_parser is not None:
        results = parse_messages_dual(
            messages,
            claude_parser=NLPParser(),
            gemini_parser=_gemini_parser,
            cover_only=False,
        )
    else:
        parser = NLPParser()
        results = parse_messages(messages, parser=parser, cover_only=False)
    request_count = sum(1 for _, r in results if r.message_type == "request")
    offer_count = sum(1 for _, r in results if r.message_type == "offer")
    rejection_count = sum(1 for _, r in results if r.message_type == "rejection")
    print(
        f"  -> {len(results)} total | requests: {request_count} | offers: {offer_count} | rejections: {rejection_count}"
    )
    # Update whatsapp_monitor_runs.requests_found now that NLP has classified.
    # The monitor itself initialised this to 0; we set the real value here.
    update_run_requests_found(monitor.last_run_id, request_count)
    if not results:
        return

    print("\nSTEP 3 - Loading deduplication fingerprints...")
    existing_fps = load_recent_fingerprints(lookback_hours=2160)      # 90 days
    existing_wa_fps = load_recent_wa_fingerprints(lookback_hours=2160)  # 90 days

    print("\nSTEP 4 - Inserting WhatsApp messages...")
    inserted = skipped = 0
    wa_inserted = wa_skipped = 0
    for msg, result in results:
        ts = msg.timestamp.strftime("%Y-%m-%d %H:%M") if msg.timestamp else "?"
        print(f"\n  [{msg.channel}] {ts} - {msg.sender}")
        print(f"  Text: {msg.text[:80]}")

        # Display parsed info based on message type
        ct_label = result.coverage_type.capitalize()
        ct_conf = f"{result.coverage_type_confidence:.2f}"
        if result.message_type == "request":
            print(
                f"  [REQUEST] Teacher: {result.teacher_name} | Date: {result.class_date}"
                f" | Time: {result.class_time} | Studio: {result.studio}"
                f" | Discipline: {result.discipline_code} | Classes: {result.estimated_class_count}"
                f" | Type: {ct_label} | Conf: {ct_conf}"
            )
        elif result.message_type == "offer":
            print(
                f"  [OFFER] Teacher: {result.offering_teacher_name} | Dates: {result.offered_dates}"
                f" | Times: {result.offered_times} | Studios: {result.offered_studios}"
                f" | Disciplines: {result.offered_disciplines} | Count: {result.can_cover_count}"
                f" | Type: {ct_label} | Conf: {ct_conf}"
            )
        elif result.message_type == "rejection":
            print(
                f"  [REJECTION] Teacher: {result.declining_teacher_name}"
                f" | For: {result.declining_for_whom} | Reason: {result.rejection_reason}"
                f" | Type: {ct_label} | Conf: {ct_conf}"
            )
        else:
            # "other" — includes NLP API failures (parse_notes will contain error)
            notes = f" | Notes: {result.parse_notes[:100]}" if result.parse_notes else ""
            print(f"  [OTHER]{notes}")

        print(
            f"  Confidence: {result.confidence_score:.2f} | review: {result.auto_review_required}"
        )

        # Insert into cover_requests (request-type messages only)
        ok = insert_whatsapp_message(msg, result, existing_fps, dry_run)
        if ok:
            inserted += 1
        else:
            skipped += 1

        # Insert ALL cover-related messages into whatsapp_messages
        wa_ok = insert_to_whatsapp_messages_table(msg, result, existing_wa_fps, dry_run)
        if wa_ok:
            wa_inserted += 1
        else:
            wa_skipped += 1

    print(f'\n{"="*60}')
    print(f'Run complete{"  [DRY RUN]" if dry_run else ""}')
    print(f"  Messages read:       {len(messages)}")
    print(f"  Cover events parsed: {len(results)}")
    print()
    print(f"  cover_requests   — inserted: {inserted}  skipped (dup): {skipped}")
    print(f"  whatsapp_messages — inserted: {wa_inserted}  skipped (dup): {wa_skipped}")
    print(f'{"="*60}')


def _test_parse() -> None:
    print("Test NLP Parser - enter a message and press Enter twice.\n")
    lines = []
    try:
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
    except EOFError:
        pass
    text = "\n".join(lines).strip()
    if not text:
        print("No message entered.")
        return
    channel = input("Channel name (or blank): ").strip()
    parser = NLPParser()
    result = parser.parse(text, channel_name=channel)
    print(f"\nis_cover_request:     {result.is_cover_request}")
    print(f"confidence_score:     {result.confidence_score:.2f}")
    print(f"auto_review_required: {result.auto_review_required}")
    print(f"teacher_name:         {result.teacher_name}")
    print(f"class_date:           {result.class_date}")
    print(f"class_time:           {result.class_time}")
    print(f"class_end_time:       {result.class_end_time}")
    print(f"studio:               {result.studio}")
    print(f"discipline_code:      {result.discipline_code}")
    print(f"parse_notes:          {result.parse_notes}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="WhatsApp -> NLP -> Supabase pipeline")
    ap.add_argument("--launch", action="store_true")
    ap.add_argument("--hours", type=int, default=WHATSAPP_LOOKBACK_HOURS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test-parse", action="store_true")
    ap.add_argument(
        "--all-messages",
        action="store_true",
        help="Insert ALL scraped messages into whatsapp_messages (not just cover-related)."
             " Useful for verifying NLP classification.",
    )
    ap.add_argument(
        "--clear-db",
        action="store_true",
        help="Clear old entries from cover_requests table",
    )
    ap.add_argument(
        "--clear-all",
        action="store_true",
        help="Clear ALL entries from cover_requests table (⚠️ use with caution)",
    )
    ap.add_argument(
        "--older-than-days",
        type=int,
        help="Only clear entries older than N days (with --clear-db)",
    )
    args = ap.parse_args()

    if args.clear_all:
        clear_cover_requests(older_than_days=None, confirm=True)
    elif args.clear_db:
        clear_cover_requests(older_than_days=args.older_than_days or 0, confirm=True)
    elif args.test_parse:
        _test_parse()
    else:
        run(
            lookback_hours=args.hours,
            launch_mode=args.launch,
            dry_run=args.dry_run,
            all_messages=args.all_messages,
        )
