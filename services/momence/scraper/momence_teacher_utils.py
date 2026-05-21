"""
momence_teacher_utils.py
========================
Shared helpers for extracting teacher / substitute information from the
Momence v2 per-session detail endpoint
    GET /api/v2/host/sessions/{id}
(documented at api.docs.momence.com/reference/apiv2hostsessionscontroller_getsession).

Used by:
  * momence_sessions_api.py — enriches every session with a per-session
    detail call so the produced CSV is fully populated in one pass.
  * backfill_teacher.py     — repairs an existing momence_classes_*.csv
    that was generated before the enrichment pass existed.

Verified live response shape (session 116740712, 2026-05-07):

    {
      "id": 116740712,
      "teacher":         { "id": 63161, "firstName": "Jess", "lastName": "Elkington", ... },
      "originalTeacher": { "id": 63161, "firstName": "Jess", "lastName": "Elkington", ... },
      "additionalTeachers": null,
      ...
    }

Field semantics:
  * teacher         — currently assigned teacher (= the substitute when
                      one has been put in, otherwise the regular teacher).
  * originalTeacher — originally scheduled teacher; equals teacher when
                      no substitution.
  * Substitution    — detected by teacher.id != originalTeacher.id.
  * additionalTeachers — assistant teachers. Ritual does NOT currently
                      use these; the field is always null and is
                      intentionally ignored.

Supabase note: any teachers table that mirrors Momence staff should
persist the Momence teacher.id (e.g. as `momence_teacher_id`) so
bookings, sessions and class-customer rows can be joined to a canonical
teacher record. The id is more stable than email.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

# ── CSV column constants — used by both enrichment and backfill ──────────────
CSV_TEACHER_COL       = "Teacher"
CSV_TEACHER_ID_COL    = "Teacher ID"
CSV_SUBSTITUTE_COL    = "Substitute"
CSV_SUBSTITUTE_ID_COL = "Substitute ID"

# ── Per-session retry tuning ─────────────────────────────────────────────────
MAX_RETRIES_PER_SESSION = 3
RETRY_BACKOFF_SECS      = 5


def extract_person_name(obj: Any) -> Optional[str]:
    """Return a display name from a teacher-shaped object, or None.

    Handles the most common shapes returned by Momence:
      * dict with 'name'                       -> "Jane Smith"
      * dict with 'firstName' + 'lastName'     -> "Jane Smith"
      * dict with 'displayName'                -> as-is
      * dict with 'user': { ... }              -> recurse into nested user
      * plain string                           -> as-is
      * list of any of the above               -> comma-joined
    """
    if obj is None:
        return None
    if isinstance(obj, str):
        s = obj.strip()
        return s or None
    if isinstance(obj, list):
        names = [extract_person_name(o) for o in obj]
        names = [n for n in names if n]
        return ", ".join(names) if names else None
    if isinstance(obj, dict):
        for key in ("displayName", "name", "fullName"):
            if obj.get(key):
                return str(obj[key]).strip()
        first = (obj.get("firstName") or "").strip()
        last  = (obj.get("lastName")  or "").strip()
        if first or last:
            return f"{first} {last}".strip()
        if isinstance(obj.get("user"), dict):
            return extract_person_name(obj["user"])
    return None


def name_and_id(obj: Any) -> Tuple[Optional[str], Optional[str]]:
    """Return (name, id) from a person-shaped object, or (None, None)."""
    name = extract_person_name(obj)
    pid: Optional[str] = None
    if isinstance(obj, dict):
        if obj.get("id") is not None:
            pid = str(obj["id"])
        elif isinstance(obj.get("user"), dict) and obj["user"].get("id") is not None:
            pid = str(obj["user"]["id"])
    elif isinstance(obj, list):
        first = next((o for o in obj if isinstance(o, dict) and o.get("id") is not None), None)
        if first is not None:
            pid = str(first["id"])
    return name, pid


def extract_teacher_info(payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Pull teacher / substitute name and id from a /host/sessions/{id} response.

    Returns a dict with keys:
        teacher_name, teacher_id, substitute_name, substitute_id

    See the module docstring for field semantics. additionalTeachers is
    intentionally ignored — Ritual does not currently use them.
    """
    body = payload.get("payload") if isinstance(payload, dict) and "payload" in payload else payload
    if not isinstance(body, dict):
        return {"teacher_name": None, "teacher_id": None,
                "substitute_name": None, "substitute_id": None}

    # ── Primary teacher (who is teaching now) ────────────────────────────
    teacher_obj: Any = None
    for key in ("teacher", "instructor", "host", "primaryTeacher"):
        if body.get(key):
            teacher_obj = body[key]
            break
    if teacher_obj is None:
        for key in ("teachers", "instructors", "hosts"):
            if body.get(key):
                teacher_obj = body[key]
                break

    teacher_name, teacher_id = name_and_id(teacher_obj)

    # ── Substitute detection ─────────────────────────────────────────────
    substitute_name: Optional[str] = None
    substitute_id:   Optional[str] = None
    original_obj = body.get("originalTeacher")
    if (
        isinstance(teacher_obj, dict)
        and isinstance(original_obj, dict)
        and teacher_obj.get("id") is not None
        and original_obj.get("id") is not None
        and teacher_obj.get("id") != original_obj.get("id")
    ):
        substitute_name, substitute_id = name_and_id(original_obj)

    # Defensive fallback only — Momence does not currently expose an
    # explicit substitute field; this guards against future schema
    # changes.
    if not substitute_name:
        for key in ("substitute", "substituteTeacher", "covering", "coveringTeacher"):
            if body.get(key):
                substitute_name, substitute_id = name_and_id(body[key])
                if substitute_name:
                    break

    return {
        "teacher_name":    teacher_name,
        "teacher_id":      teacher_id,
        "substitute_name": substitute_name,
        "substitute_id":   substitute_id,
    }


def fetch_session_detail(client, session_id: Any) -> Dict[str, Any]:
    """GET /api/v2/host/sessions/{id} with a small retry loop.

    `client` must be an authenticated MomenceAPIClient.  The function
    uses its `_make_request` helper which already handles the bearer
    token, refresh, and basic non-2xx debug logging.
    """
    endpoint = f"/api/v2/host/sessions/{session_id}"
    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES_PER_SESSION + 1):
        try:
            return client._make_request("GET", endpoint)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < MAX_RETRIES_PER_SESSION:
                time.sleep(RETRY_BACKOFF_SECS)
            else:
                raise
    raise last_exc  # type: ignore[misc]


def ensure_id_columns(fieldnames: List[str]) -> List[str]:
    """Return a fieldnames list with Teacher ID / Substitute ID inserted.

    Inserts CSV_TEACHER_ID_COL immediately after CSV_TEACHER_COL and
    CSV_SUBSTITUTE_ID_COL immediately after CSV_SUBSTITUTE_COL.
    Idempotent — does nothing if the columns are already present.
    """
    fields = list(fieldnames)
    if CSV_TEACHER_COL in fields and CSV_TEACHER_ID_COL not in fields:
        idx = fields.index(CSV_TEACHER_COL)
        fields.insert(idx + 1, CSV_TEACHER_ID_COL)
    if CSV_SUBSTITUTE_COL in fields and CSV_SUBSTITUTE_ID_COL not in fields:
        idx = fields.index(CSV_SUBSTITUTE_COL)
        fields.insert(idx + 1, CSV_SUBSTITUTE_ID_COL)
    return fields
