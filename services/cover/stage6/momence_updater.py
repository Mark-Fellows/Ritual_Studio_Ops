"""
momence_updater.py — Stage 6
=============================
Interfaces with the Momence API for session-level operations needed
during the cancellation and cover-transfer workflow:

  • Fetch a specific session by ID
  • Fetch all booked clients for a session
  • Attempt session cancellation via Momence API (best-effort;
    the Momence admin API does not always expose a public cancel
    endpoint — the workflow degrades gracefully and flags any
    manual steps required)

Usage
-----
    from stage6.momence_updater import get_session_details, get_booked_clients

    client = MomenceAPIClient()
    client.authenticate()

    session = get_session_details(client, session_id=12345678)
    clients = get_booked_clients(client, session_id=12345678)
    # clients → list of dicts: {first_name, last_name, email, phone, member_id}
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta, time

# Allow imports from project root and Momence data directory
sys.path.insert(0, str(Path(__file__).parent.parent))

# RSO Phase 3: config.py sets services/momence/ on sys.path
from momence_api_client import MomenceAPIClient  # noqa: E402 (path set by config)


# ─────────────────────────────────────────────────────────────────────────────
# Session retrieval
# ─────────────────────────────────────────────────────────────────────────────

def get_session_details(
    client: MomenceAPIClient,
    session_id: int | str,
) -> dict | None:
    """
    Retrieve a single Momence session by its numeric ID.

    Tries the direct get_session() method first; falls back to a
    narrow date-windowed get_sessions() search if the single-session
    endpoint is unavailable.

    Returns the session dict, or None if not found.
    """
    session_id = int(session_id)

    # Attempt 1: direct single-session lookup
    try:
        result = client.get_session(session_id)
        if isinstance(result, dict) and result.get('id') == session_id:
            return result
        if isinstance(result, list) and result:
            return result[0]
    except (AttributeError, Exception):
        pass  # method may not exist; fall through

    # Attempt 2: search a ±7-day window and match by ID
    print(f'  Direct session lookup unavailable — searching by date window…')
    try:
        now   = datetime.now()
        start = now - timedelta(days=7)
        end   = now + timedelta(days=90)

        page = 0
        while True:
            batch = client.get_sessions(
                start_date=start, end_date=end, page=page, page_size=100
            )
            if not batch:
                break
            if isinstance(batch, dict):
                batch = batch.get('payload') or []
            for s in batch:
                if isinstance(s, dict) and int(s.get('id') or 0) == session_id:
                    return s
            if len(batch) < 100:
                break
            page += 1
    except Exception as e:
        print(f'  Warning: session search failed: {e}')

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Booked clients
# ─────────────────────────────────────────────────────────────────────────────

def _extract_client(booking: dict) -> dict | None:
    """
    Extract contact details from a Momence booking record.
    Returns a normalised client dict or None if no useful data found.
    """
    # Member info may sit at top level or nested under 'member' / 'user'
    member = (
        booking.get('member') or
        booking.get('user') or
        booking.get('client') or
        booking
    )
    if not isinstance(member, dict):
        return None

    first = (
        member.get('firstName') or member.get('first_name') or
        booking.get('firstName') or booking.get('first_name') or ''
    ).strip()
    last = (
        member.get('lastName') or member.get('last_name') or
        booking.get('lastName') or booking.get('last_name') or ''
    ).strip()
    email = (
        member.get('email') or
        booking.get('email') or ''
    ).strip().lower()
    phone = (
        member.get('phoneNumber') or member.get('phone') or
        booking.get('phoneNumber') or booking.get('phone') or ''
    ).strip()
    member_id = (
        member.get('id') or
        booking.get('memberId') or booking.get('member_id') or
        booking.get('userId') or None
    )

    # Require at least an email or a name to be useful
    if not email and not first:
        return None

    return {
        'first_name': first,
        'last_name':  last,
        'full_name':  f'{first} {last}'.strip() or 'Client',
        'email':      email or None,
        'phone':      phone or None,
        'member_id':  str(member_id) if member_id else None,
        'booking_id': str(booking.get('id') or booking.get('bookingId') or ''),
        'booking_status': booking.get('status') or booking.get('bookingStatus') or '',
    }


def get_booked_clients(
    client: MomenceAPIClient,
    session_id: int | str,
    include_waitlist: bool = False,
) -> list[dict]:
    """
    Fetch all booked (and optionally waitlisted) clients for a Momence session.

    Returns a list of normalised client dicts:
        first_name, last_name, full_name, email, phone, member_id,
        booking_id, booking_status

    Clients without an email address are included (for completeness in
    the caller's stats) but cannot receive email notifications.
    """
    session_id = int(session_id)
    clients: list[dict] = []

    try:
        raw = client.get_session_bookings(session_id)
    except AttributeError:
        # Try alternative method name
        try:
            raw = client.get_bookings(session_id)
        except Exception as e:
            print(f'  Warning: could not fetch bookings for session {session_id}: {e}')
            return []
    except Exception as e:
        print(f'  Warning: get_session_bookings error for {session_id}: {e}')
        return []

    # Normalise response envelope
    if isinstance(raw, dict):
        raw = raw.get('payload') or raw.get('bookings') or raw.get('data') or []
    if not isinstance(raw, list):
        print(f'  Warning: unexpected bookings response type: {type(raw)}')
        return []

    for booking in raw:
        if not isinstance(booking, dict):
            continue

        # Filter out cancellations unless caller wants them
        status = (booking.get('status') or '').lower()
        if status in ('cancelled', 'canceled', 'no_show') and not include_waitlist:
            continue
        if 'waitlist' in status and not include_waitlist:
            continue

        c = _extract_client(booking)
        if c:
            clients.append(c)

    # Deduplicate by email (keep first occurrence)
    seen_emails: set[str] = set()
    unique: list[dict] = []
    for c in clients:
        key = c['email'] or c['booking_id']
        if key not in seen_emails:
            seen_emails.add(key)
            unique.append(c)

    print(f'  Found {len(unique)} booked clients for session {session_id}')
    return unique


# ─────────────────────────────────────────────────────────────────────────────
# Session cancellation (best-effort)
# ─────────────────────────────────────────────────────────────────────────────

def cancel_session_in_momence(
    client: MomenceAPIClient,
    session_id: int | str,
) -> tuple[bool, str]:
    """
    Attempt to cancel a Momence session via the API.

    Returns:
        (True,  'ok')                   — session cancelled via API
        (False, 'api_not_supported')    — Momence does not expose this endpoint
        (False, 'error: <message>')     — API call failed

    The caller should always log the result and instruct the admin
    to verify/complete the cancellation in the Momence admin UI when
    this returns False.
    """
    session_id = int(session_id)

    # Try common method names for session cancellation
    for method_name in ('cancel_session', 'delete_session', 'void_session'):
        method = getattr(client, method_name, None)
        if method is None:
            continue
        try:
            result = method(session_id)
            if result is not False:
                return True, 'ok'
        except Exception as e:
            return False, f'error: {e}'

    return False, 'api_not_supported'


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: build session summary for notifications
# ─────────────────────────────────────────────────────────────────────────────

def build_session_summary(session: dict | None, request: dict) -> dict:
    """
    Merge Momence session data with the cover_request fields to produce
    a single dict suitable for email template population.

    Falls back to cover_request fields when session data is absent.
    """
    s = session or {}

    # Class name
    class_name = (
        s.get('name') or s.get('title') or
        request.get('class_name_raw') or
        request.get('discipline_code') or
        'class'
    )

    # Date
    raw_start = s.get('startsAt') or s.get('startTime') or s.get('start_time') or ''
    if raw_start:
        try:
            dt = datetime.fromisoformat(raw_start.replace('Z', '+00:00'))
            session_date = dt.strftime('%A %-d %B %Y')
            session_time = dt.strftime('%-I:%M%p').lower()
        except (ValueError, AttributeError):
            session_date = request.get('class_date') or 'TBC'
            session_time = request.get('class_time') or 'TBC'
    else:
        d = request.get('class_date') or ''
        t = request.get('class_time') or ''
        try:
            session_date = date.fromisoformat(d).strftime('%A %-d %B %Y') if d else 'TBC'
        except ValueError:
            session_date = d or 'TBC'
        try:
            session_time = time.fromisoformat(t).strftime('%-I:%M%p').lower() if t else 'TBC'
        except (ValueError, AttributeError):
            session_time = t or 'TBC'

    # Studio / location
    loc_obj = s.get('inPersonLocation') or s.get('location') or {}
    studio = (
        (loc_obj.get('name') if isinstance(loc_obj, dict) else str(loc_obj or '')) or
        request.get('studio') or 'TBC'
    )

    # Teacher
    teacher_obj = s.get('teacher') or {}
    teacher_name = ''
    if isinstance(teacher_obj, dict):
        teacher_name = (
            f"{teacher_obj.get('firstName', '')} {teacher_obj.get('lastName', '')}".strip()
        )
    if not teacher_name:
        teacher_name = request.get('requesting_teacher_name_raw') or 'your teacher'

    return {
        'class_name':    class_name,
        'session_date':  session_date,
        'session_time':  session_time,
        'studio':        studio,
        'teacher_name':  teacher_name,
        'session_id':    session_id if session else None,
        'spots_left':    s.get('spotsLeft'),
        'capacity':      s.get('capacity'),
    }
