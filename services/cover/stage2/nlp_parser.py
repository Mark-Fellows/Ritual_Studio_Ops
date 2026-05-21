"""
nlp_parser.py — Stage 2
========================
Uses the Claude API to extract structured cover-request data from raw
WhatsApp messages.

For each message the parser returns a ParseResult with:
  - is_cover_request  (bool)   — is this a cover request at all?
  - confidence_score  (float)  — 0.0–1.0 overall confidence
  - teacher_name      (str)    — name of teacher needing cover
  - class_date        (date)   — date of the class
  - class_times       (list[time])  — all class start times mentioned
  - class_time        (time)   — primary/first class time (backward compat)
  - studios           (list[str]) — all studios mentioned ['Robina', 'Palm Beach']
  - studio            (str)    — primary/first studio (backward compat)
  - discipline_codes  (list[str]) — all disciplines [reformer/yin/barre/yoga/mat_pilates]
  - discipline_code   (str)    — primary/first discipline code (backward compat)
  - class_name_raw    (str)    — original class name from message
  - parse_notes       (str)    — NLP rationale and ambiguity explanation

Usage
-----
    from nlp_parser import NLPParser
    parser = NLPParser()
    result = parser.parse(message_text, channel_name='RITUAL DIARY')
"""

import json
import os
import sys
import re
from datetime import date, time, datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    ANTHROPIC_API_KEY,
    NLP_MODEL,
    NLP_CONFIDENCE_THRESHOLD,
    ACTIVE_STUDIOS,
)

# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ParseResult:
    # Classification & Type
    is_cover_request: bool = False  # Backward compat: True if request/offer/rejection
    message_type: str = "other"  # 'request', 'offer', 'rejection', or 'other'
    confidence_score: float = 0.0
    auto_review_required: bool = True

    # Fields for REQUEST messages (teacher needs cover)
    teacher_name: Optional[str] = None
    class_date: Optional[date] = None
    class_time: Optional[time] = None  # first/primary time
    class_end_time: Optional[time] = None  # estimated if duration known
    studio: Optional[str] = None  # first/primary studio
    discipline_code: Optional[str] = None  # first/primary discipline
    class_name_raw: Optional[str] = None
    class_times: Optional[list[time]] = field(default_factory=lambda: None)
    class_dates: Optional[list[date]] = field(default_factory=lambda: None)  # ALL specific dates the message lists
    studios: Optional[list[str]] = field(default_factory=lambda: None)
    discipline_codes: Optional[list[str]] = field(default_factory=lambda: None)
    estimated_class_count: int | str | None = None  # e.g. 4 or "?" if ambiguous

    # Structured per-clause groupings added 2026-05-16. Each entry is a dict
    # with keys "dates" (list[str] ISO), "times" (list[str] ISO), "studios"
    # (list[str]) and "disciplines" (list[str]). Claude is asked to populate
    # this whenever the message describes more than one (date, studio, time)
    # clause - which is most multi-class requests. cover_processor.py
    # converts these dicts into CoverRequestGroup objects before passing
    # them to the resolver, which then matches each group independently
    # instead of cross-joining the flat arrays above. Falls back to the
    # flat arrays if Claude doesn't emit groups for a given message.
    cover_groups: Optional[list[dict]] = field(default_factory=lambda: None)

    # Fields for OFFER messages (teacher offering to cover)
    offering_teacher_name: Optional[str] = None  # Who is offering
    offered_dates: Optional[list[date]] = field(default_factory=lambda: None)
    offered_times: Optional[list[time]] = field(default_factory=lambda: None)
    offered_studios: Optional[list[str]] = field(default_factory=lambda: None)
    offered_disciplines: Optional[list[str]] = field(default_factory=lambda: None)
    can_cover_count: int | str | None = None  # Estimated classes they can cover

    # Fields for REJECTION messages (teacher declining cover)
    declining_teacher_name: Optional[str] = None  # Who is declining
    declining_for_whom: Optional[str] = None  # Whose class/cover request
    rejection_reason: Optional[str] = None
    linked_to_cover_request_id: Optional[str] = None  # If we can link to a request

    # Metadata
    parse_notes: str = ""
    raw_llm_response: str = ""
    model_used: str = ""

    # Coverage type classification (Phase 2)
    coverage_type: str = "both"                    # 'temporary', 'permanent', or 'both'
    coverage_type_confidence: float = 1.0          # 0.0–1.0
    coverage_type_reasoning: Optional[str] = None  # Claude's reasoning

    # Dual-model fields — populated when both Claude and Gemini are queried
    nlp_claude_type: Optional[str] = None          # Claude's raw message_type
    nlp_gemini_type: Optional[str] = None          # Gemini's raw message_type
    nlp_disparity_score: Optional[float] = None    # 0.0 = full agreement, 1.0 = max disagreement
    nlp_primary_source: str = "anthropic"          # which model drove message_type / confidence_score

    def to_db_dict(
        self, channel_db_id: str, raw_message: str, message_timestamp: datetime | None
    ) -> dict:
        """
        Serialise to a dict ready for INSERT into whatsapp_messages table.
        Handles requests, offers, and rejections.
        Arrays are serialized as JSON for JSONB storage.
        """
        result = {
            "whatsapp_channel_id": channel_db_id,
            "raw_message": raw_message,
            "message_timestamp": (
                message_timestamp.isoformat() if message_timestamp else None
            ),
            "message_type": self.message_type,
            "confidence_score": round(self.confidence_score, 3),
            "auto_review_required": self.auto_review_required,
            "parse_notes": self.parse_notes,
            "coverage_type": self.coverage_type,
            "coverage_type_confidence": round(self.coverage_type_confidence, 2),
        }

        if self.message_type == "request":
            result.update(
                {
                    "requesting_teacher_name_raw": self.teacher_name,
                    "class_date": (
                        self.class_date.isoformat() if self.class_date else None
                    ),
                    "class_time": (
                        self.class_time.isoformat() if self.class_time else None
                    ),
                    "class_end_time": (
                        self.class_end_time.isoformat() if self.class_end_time else None
                    ),
                    "studio": self.studio,
                    "discipline_code": self.discipline_code,
                    "class_name_raw": self.class_name_raw,
                    "class_times": (
                        json.dumps([t.isoformat() for t in self.class_times])
                        if self.class_times
                        else None
                    ),
                    "class_dates": (
                        json.dumps([d.isoformat() for d in self.class_dates])
                        if self.class_dates
                        else None
                    ),
                    "studios": json.dumps(self.studios) if self.studios else None,
                    "discipline_codes": (
                        json.dumps(self.discipline_codes)
                        if self.discipline_codes
                        else None
                    ),
                    "estimated_class_count": self.estimated_class_count,
                    "status": "pending_review",
                }
            )
        elif self.message_type == "offer":
            result.update(
                {
                    "offering_teacher_name_raw": self.offering_teacher_name,
                    "offered_dates": (
                        json.dumps([d.isoformat() for d in self.offered_dates])
                        if self.offered_dates
                        else None
                    ),
                    "offered_times": (
                        json.dumps([t.isoformat() for t in self.offered_times])
                        if self.offered_times
                        else None
                    ),
                    "offered_studios": (
                        json.dumps(self.offered_studios)
                        if self.offered_studios
                        else None
                    ),
                    "offered_disciplines": (
                        json.dumps(self.offered_disciplines)
                        if self.offered_disciplines
                        else None
                    ),
                    "can_cover_count": self.can_cover_count,
                    "status": "offer_pending",
                }
            )
        elif self.message_type == "rejection":
            result.update(
                {
                    "declining_teacher_name_raw": self.declining_teacher_name,
                    "declining_for_whom": self.declining_for_whom,
                    "rejection_reason": self.rejection_reason,
                    "linked_to_cover_request_id": self.linked_to_cover_request_id,
                    "status": "rejection",
                }
            )

        return result


# ─────────────────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an assistant that analyses WhatsApp messages from yoga and pilates studio teachers at Ritual Studios (locations: Robina, Palm Beach — Queensland, Australia).

DOMAIN NOTE: In this studio context, "covers" or "a cover" means a class substitute — a teacher who "needs covers" or "needs someone to cover" is asking for another teacher to take their scheduled classes. This is the ONLY meaning of "cover/covers" in these messages.

Your job is to CLASSIFY and EXTRACT structured information from three types of messages:

1. **COVER REQUEST** — A teacher asks/needs someone to cover their class
2. **COVER OFFER** — A teacher volunteers or confirms they can cover certain classes
3. **REJECTION/DECLINE** — A teacher says they cannot cover a class or offer

IMPORTANT: If no teacher name is explicitly mentioned in the message text, use the sender's name (provided separately) as the teacher_name. The sender is the person sending the message.

Australian date/time conventions apply:
- Dates are written day/month (e.g. "6/5" = 6 May, not 6 June)
- Times may be written as "9am", "9:15am", "9:15", etc.
- Days of the week are sometimes used without a date (e.g. "this Thursday")

Discipline codes (use exactly these strings):
  reformer, yin, barre, yoga, mat_pilates

Studios:
  Robina, Palm Beach

You MUST respond with ONLY valid JSON — no markdown, no explanation outside the JSON.

JSON schema (adjust fields based on message_type):
{
  "message_type": "request" | "offer" | "rejection" | "other" (classify first!),
  "is_cover_request": boolean (true if request/offer/rejection, false if other),
  "confidence_score": float (0.0–1.0),

  **IF message_type = "request":**
  "teacher_name": string or null (who needs cover),
  "class_date_iso": "YYYY-MM-DD" or null (first/primary date),
  "class_dates_iso": ["YYYY-MM-DD", ...] or null (ALL specific dates the message names — see notes below),
  "class_time_iso": "HH:MM:SS" or null (first/primary time),
  "class_times_iso": ["HH:MM:SS", ...] or null (ALL times),
  "class_duration_minutes": integer or null,
  "studio": "Robina" | "Palm Beach" or null (first),
  "studios": ["Robina", "Palm Beach"] or null (ALL),
  "discipline_code": discipline code or null (first),
  "discipline_codes": [discipline codes] or null (ALL),
  "class_name_raw": string or null,
  "estimated_class_count": integer 1–100 or "?" (use SKILL-estimate-class-count),
  "cover_groups": [
      { "dates": ["YYYY-MM-DD", ...], "times": ["HH:MM:SS", ...],
        "studios": ["Robina"|"Palm Beach", ...],
        "disciplines": [discipline codes, ...] },
      ...
  ] or null (one entry per (date, studio, time, discipline) clause — see notes below),

  **IF message_type = "offer":**
  "offering_teacher_name": string or null (who is offering),
  "offered_dates_iso": ["YYYY-MM-DD", ...] or null (what dates they can cover),
  "offered_times_iso": ["HH:MM:SS", ...] or null (what times),
  "offered_studios": ["Robina", "Palm Beach"] or null (where),
  "offered_disciplines": [discipline codes] or null (what types),
  "can_cover_count": integer 1–100 or "?" (estimated classes),

  **IF message_type = "rejection":**
  "declining_teacher_name": string or null (who is declining),
  "declining_for_whom": string or null (whose cover request or class, if mentioned),
  "rejection_reason": string or null (e.g., "not available", "already committed"),

  **ALWAYS INCLUDE:**
  "coverage_type": "temporary" | "permanent" | "both",
  "coverage_type_confidence": float (0.0–1.0),
  "coverage_type_reasoning": string (brief explanation of signals found),
  "parse_notes": string (explain confidence, context, ambiguities)
}

COVERAGE TYPE CLASSIFICATION:
For every message (request, offer, or rejection), classify coverage_type as one of:
- **temporary**: signals include "ASAP", "this week", "next [day]", "one-off", "temporarily", "short-term", "fill-in", "just this once", "only this once", "urgent", specific single dates
- **permanent**: signals include "ongoing", "permanent", "permanently", "indefinitely", "taking over", "till further notice", "long-term", "regular", "standing", "from [date] onwards", "replacing", "leaving"
- **both**: signals include "temporary or permanent", "flexible", "either way", "can do either", "open to both", or when the request is explicitly open to either arrangement
- Default to **"both"** if signals are absent or ambiguous.

Set coverage_type_confidence to reflect how clear the signals are (1.0 = explicit signal word present, 0.7 = inferred from context, 0.5 = ambiguous/defaulted).

Message Type Classification:
- **REQUEST**: "Can someone cover my...", "I need cover for...", "I need covers...", "I need some covers...", "Can you cover for me...", "I'm unable to teach...", "I'm going away [and need covers]...", "I'll be away...", "I'm away from [date]...", "Anyone able to cover...", "Does anyone have...", "need someone for my classes..."
  → NOTE: A teacher saying they are going away / travelling / on leave and need covers IS a REQUEST even when phrased informally. "Need covers" is equivalent to "need cover".
- **OFFER**: "I can cover...", "I'm available to cover...", "I'll teach that class", "Count me in", "I can help with...", "I can do [day/class]...", "I'm free [date]...", "Happy to take..."
  → NOTE: A reply such as "I can help with the Tuesdays" in a teacher channel IS a COVER OFFER even without the word "cover" — infer from context that it is responding to a cover request.
- **REJECTION**: "I can't cover...", "Not available...", "Can't do that...", "Already committed", "Sorry I can't...", "Unfortunately I'm not free..."

Confidence guidelines:
  1.0 — type clearly identified, all fields extracted with certainty
  0.85 — type clear, all key fields present, minor ambiguity (e.g. am/pm inferred)
  0.75 — type clear, key fields present, arrays populated clearly
  0.6 — one important field is missing or uncertain
  0.4 — two fields missing/uncertain or significant ambiguity about intent
  0.2 — message might be cover-related but very little parseable information
  0.0 — not a cover request/offer/rejection (message_type = "other", is_cover_request = false)

If message_type = "other", is_cover_request must be false, all other fields null, confidence_score = 0.0.

**ENUMERATING CLASS DATES (for requests):**
Always populate "class_dates_iso" with EVERY specific date the message names — not just the first one. This is critical for downstream cross-checking against the Momence schedule.

Rules:
  - If the message lists individual dates (e.g. "Tuesday 2nd June, Tuesday 9th June, Tuesday 16th June, Friday 29th May, Friday 5th June, Friday 12th June, Friday 19th June"), return all 7 ISO dates.
  - If the message gives a date range like "29 May to 19 June" together with named weekdays ("my Tuesdays and Fridays", "my Mat Pilates classes"), expand the range into the specific weekday occurrences and return them all.
  - If the message gives ONLY a date range with no weekday clues (e.g. "I'm away the week of June 1st"), set "class_dates_iso" to null and capture the range in parse_notes; do not guess.
  - Use the message's own current-year context. Australian conventions: "2nd June" means 2 June, not June 2.
  - "class_date_iso" should be set to the EARLIEST of the listed dates; "class_dates_iso" is the full list including that earliest date.

Examples:
  "Cover me Tuesday 6:15pm" (single occurrence) → class_dates_iso: ["2026-MM-DD"] (the next Tuesday)
  "Tuesdays 2/9/16 June 5:15 and 7:30" → class_dates_iso: ["2026-06-02", "2026-06-09", "2026-06-16"]
  "Away 29 May – 19 June, my Tuesday & Friday Mat Pilates" → class_dates_iso: ["2026-05-29", "2026-06-02", "2026-06-05", "2026-06-09", "2026-06-12", "2026-06-16", "2026-06-19"]

**STRUCTURED COVER GROUPS (for requests) — CRITICAL FOR CORRECT MATCHING:**
Populate "cover_groups" with one entry per clause of the request. A clause is one combination of (dates, times, studios, discipline) that the message asks cover for. Each clause typically corresponds to one line of the message.

The downstream resolver matches each group independently and does NOT cross-join across groups. So if the message says:

  "18/5 PB - 8:30, 9:30 reformer
   20/5 Robina - 7:15, 8:15 reformer"

it MUST be returned as TWO groups:

  cover_groups: [
    {"dates": ["2026-05-18"], "times": ["08:30:00", "09:30:00"], "studios": ["Palm Beach"], "disciplines": ["reformer"]},
    {"dates": ["2026-05-20"], "times": ["07:15:00", "08:15:00"], "studios": ["Robina"],     "disciplines": ["reformer"]}
  ]

NOT one combined group, because that would imply the requester wants cover at Palm Beach on 20/5 (they do not) and at Robina on 18/5 (they do not).

Rules:
  - Within a group, every date applies to every time, every studio and every discipline in that same group. So if a single clause says "Mondays and Fridays 5:15 & 7:30 Reformer at Robina", that's ONE group with two dates, two times, one studio, one discipline.
  - If the message has only one clause (single date+time+studio+discipline, or a recurring pattern with one studio and one discipline), still return one group containing that clause.
  - If the message has no time, studio or discipline information for a clause, set that field to an empty list ([]) — empty means "any" downstream.
  - "cover_groups" must always be consistent with "class_dates_iso", "class_times_iso", "studios" and "discipline_codes" — those flat fields are the union of all groups.
  - If you genuinely cannot tell which time/studio belongs to which date, fall back to one combined group containing all of them and explain the ambiguity in parse_notes. The legacy cross-join will then apply.
  - cover_groups may be null if the message is not a request, has no parseable structure, or is purely free-form (e.g. "Anyone free this week?").

More examples:

  "Anyone available next Thursday 21/05 at 5pm BARRE at Palm Beach?"
    → cover_groups: [
        {"dates": ["2026-05-21"], "times": ["17:00:00"], "studios": ["Palm Beach"], "disciplines": ["barre"]}
      ]

  "I need cover for my Tuesday & Thursday Mat Pilates classes the week of 9 June — Tue 5:15 and 7:30 at Robina; Thu 5:15, 7:30 and 8:30 at Robina"
    → cover_groups: [
        {"dates": ["2026-06-09"], "times": ["05:15:00", "07:30:00"],            "studios": ["Robina"], "disciplines": ["mat_pilates"]},
        {"dates": ["2026-06-11"], "times": ["05:15:00", "07:30:00", "08:30:00"], "studios": ["Robina"], "disciplines": ["mat_pilates"]}
      ]

  "Hey team — anyone able to cover my 4:30pm reformer at Robina tomorrow?"
    → cover_groups: [
        {"dates": ["2026-MM-DD"], "times": ["16:30:00"], "studios": ["Robina"], "disciplines": ["reformer"]}
      ]

**ESTIMATED CLASS COUNT (for requests and offers):**
Calculate estimated_class_count by multiplying dimensions:
  - Count of distinct times (6:15 + 9:15 = 2)
  - × Count of distinct studios (Robina + Palm Beach = 2)
  - × Count of distinct dates (Mon + Tue = 2, or ~4 weeks if recurring)

**IMPORTANT — default to 1, not "?":**
If you can identify exactly one date, one time, and one studio (even if the message uses
natural-language singulars like "a class", "my class", "single", "one class", or simply
names one date and one time), the result is 1 × 1 × 1 = **1**. Do NOT return "?" for
these cases. Only return "?" when you genuinely cannot determine even one of the three
dimensions (e.g. no date, no time, and no studio are mentioned at all).

Examples:
  "Cover me Tuesday 6:15pm" → 1 time × 1 studio × 1 day = **1 class**
  "Can anyone cover my Yoga Sat 16 May 8am PB?" → 1 time × 1 studio × 1 day = **1 class**
  "Can anyone cover my single Barre class Thu 21 May 5pm PB?" → 1 × 1 × 1 = **1 class**
  "I need cover for a class on Monday" → 1 time (unknown but single) × 1 studio × 1 day = **1 class**
  "Tuesday 6:15 and 9:15" → 2 times × 1 studio × 1 day = **2 classes**
  "6:15 at both studios" → 1 time × 2 studios × 1 day = **2 classes**
  "6:15 and 9:15 at both studios" → 2 times × 2 studios × 1 day = **4 classes**
  "Monday and Thursday 6:15 at Robina" → 1 time × 1 studio × 2 days = **2 classes**
  "6:15 every day this week" → 1 time × 1 studio × 5 days = **5 classes**
  "6:15 for the whole month May" → 1 time × 1 studio × 4 weeks = **4 classes**
  "Tuesday and Thursday 6:15 and 9:15 at both studios" → 2 times × 2 studios × 2 days = **8 classes**
  "I need covers" (no date, no time, no studio) → **"?"** (genuinely insufficient info)

Return as integer (e.g. 4) or "?" only if you genuinely cannot determine any of the three
dimensions."""


# ─────────────────────────────────────────────────────────────────────────────
# Parser class
# ─────────────────────────────────────────────────────────────────────────────


class NLPParser:
    """
    Wraps the Anthropic Claude API to parse WhatsApp messages
    into structured cover-request data.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.model = model or NLP_MODEL
        self._client = None

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to .env or set the environment variable."
            )

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                sys.exit(
                    "anthropic package not installed. " "Run: pip install anthropic"
                )
        return self._client

    def parse(
        self,
        message_text: str,
        channel_name: str = "",
        message_date: date | None = None,
        sender_name: str | None = None,
        is_reply: bool = False,
        original_sender: str | None = None,
    ) -> ParseResult:
        """
        Parse a single WhatsApp message.

        Parameters
        ----------
        message_text : str
            Raw message text.
        channel_name : str
            Channel name for context (e.g. 'RITUAL REFORMER TEAM').
            If the channel implies a discipline (e.g. reformer channel)
            this hint is passed to the model.
        message_date : date | None
            Date the message was sent. Used to resolve relative date
            references such as "this Thursday".
        sender_name : str | None
            Name of the message sender. Used as fallback if no explicit
            teacher name is found in the message text.
        is_reply : bool
            Whether this message is a reply to another message (quoted/threaded).
        original_sender : str | None
            If is_reply is True, the name of the original message sender
            (the person requesting cover).

        Returns
        -------
        ParseResult
        """
        client = self._get_client()
        today = message_date or date.today()
        user_content = self._build_context(
            message_text, channel_name, today, sender_name, is_reply, original_sender
        )

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=1200,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text.strip()
        except Exception as e:
            return ParseResult(
                is_cover_request=False,
                confidence_score=0.0,
                parse_notes=f"API error: {e}",
            )

        return self._parse_response(raw, message_date=today, sender_name=sender_name)

    # ── Response parsing ──────────────────────────────────────────────────────

    def _parse_response(
        self, raw_json: str, message_date: date, sender_name: str | None = None
    ) -> ParseResult:
        """Convert the LLM JSON response into a ParseResult."""
        result = ParseResult(raw_llm_response=raw_json, model_used=self.model)

        # Strip markdown code fences if the model added them
        cleaned = re.sub(
            r"^```(?:json)?\s*|\s*```$", "", raw_json, flags=re.DOTALL
        ).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            result.parse_notes = f"JSON parse error: {e}. Raw: {raw_json[:200]}"
            result.confidence_score = 0.0
            result.auto_review_required = True
            return result

        # Extract top-level fields
        result.message_type = data.get("message_type", "other")
        result.is_cover_request = bool(data.get("is_cover_request", False))
        result.confidence_score = float(data.get("confidence_score", 0.0))
        result.parse_notes = data.get("parse_notes") or ""

        # Extract coverage type classification
        raw_ct = data.get("coverage_type", "both")
        if raw_ct not in ("temporary", "permanent", "both"):
            raw_ct = "both"
        result.coverage_type = raw_ct

        try:
            ct_conf = float(data.get("coverage_type_confidence", 1.0))
            ct_conf = max(0.0, min(1.0, ct_conf))
        except (TypeError, ValueError):
            ct_conf = 1.0
        result.coverage_type_confidence = ct_conf
        result.coverage_type_reasoning = data.get("coverage_type_reasoning")

        # ─────────────────────────────────────────────────────────────
        # Process based on message_type
        # ─────────────────────────────────────────────────────────────

        if result.message_type == "request":
            # Extract REQUEST fields
            result.teacher_name = data.get("teacher_name") or sender_name
            result.class_name_raw = data.get("class_name_raw")
            result.estimated_class_count = data.get("estimated_class_count")

            # Parse arrays
            class_times_iso_array = data.get("class_times_iso")
            class_dates_iso_array = data.get("class_dates_iso")
            studios_array = data.get("studios")
            discipline_codes_array = data.get("discipline_codes")

            if class_times_iso_array and isinstance(class_times_iso_array, list):
                result.class_times = []
                for time_iso in class_times_iso_array:
                    try:
                        result.class_times.append(time.fromisoformat(time_iso))
                    except (ValueError, TypeError):
                        result.parse_notes += f" [Could not parse time: {time_iso}]"
                if not result.class_times:
                    result.class_times = None

            if class_dates_iso_array and isinstance(class_dates_iso_array, list):
                result.class_dates = []
                for date_iso in class_dates_iso_array:
                    try:
                        result.class_dates.append(date.fromisoformat(date_iso))
                    except (ValueError, TypeError):
                        result.parse_notes += f" [Could not parse date: {date_iso}]"
                if not result.class_dates:
                    result.class_dates = None

            if studios_array and isinstance(studios_array, list):
                result.studios = studios_array
            if discipline_codes_array and isinstance(discipline_codes_array, list):
                result.discipline_codes = discipline_codes_array

            # Parse cover_groups (structured per-clause groupings, 2026-05-16+).
            # Stored as plain dicts so they survive JSON round-tripping; the
            # cover_processor will convert them to CoverRequestGroup objects.
            cover_groups_array = data.get("cover_groups")
            if cover_groups_array and isinstance(cover_groups_array, list):
                cleaned_groups: list[dict] = []
                for g in cover_groups_array:
                    if not isinstance(g, dict):
                        continue
                    # Keep only the canonical keys; drop unknown fields.
                    cleaned = {
                        "dates":       [d for d in (g.get("dates")       or []) if isinstance(d, str)],
                        "times":       [t for t in (g.get("times")       or []) if isinstance(t, str)],
                        "studios":     [s for s in (g.get("studios")     or []) if isinstance(s, str)],
                        "disciplines": [d for d in (g.get("disciplines") or []) if isinstance(d, str)],
                    }
                    # Skip empty groups (no info at all)
                    if any(cleaned.values()):
                        cleaned_groups.append(cleaned)
                result.cover_groups = cleaned_groups if cleaned_groups else None

            # Extract singular/primary fields
            if data.get("class_date_iso"):
                try:
                    result.class_date = date.fromisoformat(data["class_date_iso"])
                except ValueError:
                    result.parse_notes += (
                        f' [Could not parse date: {data["class_date_iso"]}]'
                    )

            if data.get("class_time_iso"):
                try:
                    result.class_time = time.fromisoformat(data["class_time_iso"])
                except ValueError:
                    result.parse_notes += (
                        f' [Could not parse time: {data["class_time_iso"]}]'
                    )
            elif result.class_times:
                result.class_time = result.class_times[0]

            if data.get("studio"):
                result.studio = data.get("studio")
            elif result.studios:
                result.studio = result.studios[0]

            if data.get("discipline_code"):
                result.discipline_code = data.get("discipline_code")
            elif result.discipline_codes:
                result.discipline_code = result.discipline_codes[0]

            # Validate studios
            valid_studios = []
            if result.studios:
                for studio in result.studios:
                    if studio in ACTIVE_STUDIOS:
                        valid_studios.append(studio)
                    else:
                        result.parse_notes += (
                            f" [Warning: studio '{studio}' not in active studios]"
                        )
                result.studios = valid_studios if valid_studios else None
                if result.studios:
                    result.studio = result.studios[0]
                else:
                    result.studio = None
            elif result.studio and result.studio not in ACTIVE_STUDIOS:
                result.parse_notes += (
                    f' [Warning: studio "{result.studio}" not in active studios]'
                )
                result.studio = None

            # Estimate end time from duration
            if result.class_time and data.get("class_duration_minutes"):
                try:
                    dur = int(data["class_duration_minutes"])
                    start_dt = datetime.combine(message_date, result.class_time)
                    end_dt = start_dt + timedelta(minutes=dur)
                    result.class_end_time = end_dt.time()
                except (ValueError, TypeError):
                    pass

        elif result.message_type == "offer":
            # Extract OFFER fields
            result.offering_teacher_name = (
                data.get("offering_teacher_name") or sender_name
            )
            # Claude is permitted to return either an int 1-100 or the
            # string "?" when the count is unknown. Supabase's
            # whatsapp_messages.can_cover_count column is INTEGER, so
            # coerce anything non-integer to None to avoid 22P02 inserts.
            raw_count = data.get("can_cover_count")
            result.can_cover_count = raw_count if isinstance(raw_count, int) else None

            # Parse offered arrays
            offered_dates_iso = data.get("offered_dates_iso")
            offered_times_iso = data.get("offered_times_iso")
            offered_studios = data.get("offered_studios")
            offered_disciplines = data.get("offered_disciplines")

            if offered_dates_iso and isinstance(offered_dates_iso, list):
                result.offered_dates = []
                for date_iso in offered_dates_iso:
                    try:
                        result.offered_dates.append(date.fromisoformat(date_iso))
                    except (ValueError, TypeError):
                        result.parse_notes += f" [Could not parse date: {date_iso}]"
                if not result.offered_dates:
                    result.offered_dates = None

            if offered_times_iso and isinstance(offered_times_iso, list):
                result.offered_times = []
                for time_iso in offered_times_iso:
                    try:
                        result.offered_times.append(time.fromisoformat(time_iso))
                    except (ValueError, TypeError):
                        result.parse_notes += f" [Could not parse time: {time_iso}]"
                if not result.offered_times:
                    result.offered_times = None

            if offered_studios and isinstance(offered_studios, list):
                # Validate offered studios
                valid_studios = [s for s in offered_studios if s in ACTIVE_STUDIOS]
                result.offered_studios = valid_studios if valid_studios else None
                if not valid_studios and offered_studios:
                    result.parse_notes += (
                        f" [Warning: some offered studios not in active list]"
                    )

            if offered_disciplines and isinstance(offered_disciplines, list):
                result.offered_disciplines = offered_disciplines

        elif result.message_type == "rejection":
            # Extract REJECTION fields
            result.declining_teacher_name = (
                data.get("declining_teacher_name") or sender_name
            )
            result.declining_for_whom = data.get("declining_for_whom")
            result.rejection_reason = data.get("rejection_reason")
            result.linked_to_cover_request_id = data.get("linked_to_cover_request_id")

        # ─────────────────────────────────────────────────────────────

        # Determine if admin review is required
        result.auto_review_required = (
            not result.is_cover_request
            or result.confidence_score < NLP_CONFIDENCE_THRESHOLD
        )

        return result

    @staticmethod
    @staticmethod
    def _build_context(
        message_text: str,
        channel_name: str,
        today,
        sender_name,
        is_reply: bool,
        original_sender,
    ) -> str:
        """Build the user-content string sent to the LLM."""
        context_lines = [
            f'Today\'s date (message was sent): {today.strftime("%A %d %B %Y")}',
            f"Channel: {channel_name}" if channel_name else "",
            f"Channel discipline hint: {NLPParser._channel_discipline_hint(channel_name)}",
            (
                f"Message sender (teacher requesting cover): {sender_name}"
                if sender_name else ""
            ),
            (
                f"This is a REPLY message. Original requester: {original_sender}"
                if is_reply and original_sender else ""
            ),
            "",
            "Message:",
            "---",
            message_text,
        ]
        return "\n".join(filter(None, context_lines))

    @staticmethod
    def _channel_discipline_hint(channel_name: str) -> str:
        """Infer a discipline hint from the channel name."""
        ch = (channel_name or "").lower()
        if "reformer" in ch:
            return "This is the Reformer channel — discipline is likely reformer."
        if "yin" in ch:
            return "This is the Yin channel — discipline is likely yin."
        if "barre" in ch:
            return "This is the Barre channel — discipline is likely barre."
        return "No channel-specific discipline hint."




# ─────────────────────────────────────────────────────────────────────────────
# Gemini parser
# ─────────────────────────────────────────────────────────────────────────────


class GeminiNLPParser(NLPParser):
    """
    Subclass of NLPParser that calls Google Gemini instead of Anthropic Claude.
    Inherits _build_context() and _parse_response() from NLPParser.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        # Do NOT call super().__init__() — we don't want the Anthropic client
        from config import GEMINI_API_KEY, GEMINI_MODEL as _GEMINI_MODEL
        self.api_key = api_key or GEMINI_API_KEY
        self.model   = model or _GEMINI_MODEL
        self._client = None

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Add it to .env."
            )

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                sys.exit(
                    "google-genai package not installed. "
                    "Run: pip install google-genai"
                )
        return self._client

    def parse(
        self,
        message_text: str,
        channel_name: str = "",
        message_date=None,
        sender_name=None,
        is_reply: bool = False,
        original_sender=None,
    ) -> ParseResult:
        from google.genai import types as _genai_types

        client = self._get_client()
        today = message_date or date.today()
        user_content = self._build_context(
            message_text, channel_name, today, sender_name, is_reply, original_sender
        )

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=user_content,
                config=_genai_types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            raw = response.text.strip()
        except Exception as e:
            return ParseResult(
                is_cover_request=False,
                confidence_score=0.0,
                parse_notes=f"Gemini API error: {e}",
            )

        return self._parse_response(raw, message_date=today, sender_name=sender_name)


# ─────────────────────────────────────────────────────────────────────────────
# Dual-model helpers
# ─────────────────────────────────────────────────────────────────────────────


def compute_disparity(r_claude: ParseResult, r_gemini: ParseResult) -> float:
    """
    Compute a disparity score (0.0 = full agreement, 1.0 = max disagreement)
    from two ParseResult objects.

    Scoring:
      +0.50  is_cover_request disagrees
      +0.35  message_type disagrees (when both agree it is cover-related)
      +0.15  confidence delta ≥ 0.30
    """
    score = 0.0
    if r_claude.is_cover_request != r_gemini.is_cover_request:
        score += 0.50
    elif r_claude.message_type != r_gemini.message_type:
        score += 0.35
    conf_delta = abs(r_claude.confidence_score - r_gemini.confidence_score)
    if conf_delta >= 0.30:
        score += 0.15
    return min(round(score, 3), 1.0)

# ─────────────────────────────────────────────────────────────────────────────
# Batch helper
# ─────────────────────────────────────────────────────────────────────────────


def parse_messages(
    messages: list,
    parser: NLPParser | None = None,
    cover_only: bool = True,
) -> list[tuple]:
    """
    Parse a list of ChannelMessage objects.

    Parameters
    ----------
    messages : list[ChannelMessage]
        As returned by WhatsAppMonitor.run().
    parser : NLPParser | None
        Reuse an existing parser (recommended to avoid re-initialising the client).
    cover_only : bool
        If True (default), return only cover-related messages (requests, offers,
        rejections). If False, return ALL messages including 'other' type — useful
        for verification and populating the whatsapp_messages audit table.
    """
    if parser is None:
        parser = NLPParser()

    results = []
    for i, msg in enumerate(messages, 1):
        print(f"  [{i}/{len(messages)}] Parsing: {msg.text[:60]}…")
        result = parser.parse(
            message_text=msg.text,
            channel_name=msg.channel,
            message_date=msg.timestamp.date() if msg.timestamp else None,
            sender_name=msg.sender,
            is_reply=msg.is_reply,
            original_sender=msg.original_sender,
        )
        if result.is_cover_request:
            msg_type = result.message_type
            if msg_type == "request":
                print(
                    f"    ✓ COVER REQUEST: {result.teacher_name} (confidence: {result.confidence_score:.2f})"
                )
            elif msg_type == "offer":
                print(
                    f"    ✓ COVER OFFER: {result.offering_teacher_name} (confidence: {result.confidence_score:.2f})"
                )
            elif msg_type == "rejection":
                print(
                    f"    ✓ REJECTION: {result.declining_teacher_name} (confidence: {result.confidence_score:.2f})"
                )
            else:
                print(
                    f"    ✓ Cover-related ({msg_type}) (confidence: {result.confidence_score:.2f})"
                )
            results.append((msg, result))
        else:
            print(f"    ─ Not cover-related (type: {result.message_type})")
            if result.parse_notes:
                print(f"    ─ Notes: {result.parse_notes[:200]}")
            if not cover_only:
                results.append((msg, result))

    return results




def parse_messages_dual(
    messages: list,
    claude_parser: NLPParser | None = None,
    gemini_parser: GeminiNLPParser | None = None,
    cover_only: bool = False,
) -> list[tuple]:
    """
    Parse messages with both Claude and Gemini, returning one result per
    message with disparity metadata attached to the winning ParseResult.

    The primary result (stored in message_type / confidence_score) is the
    higher-confidence result when the two models agree on is_cover_request;
    Claude wins ties. When models disagree on is_cover_request, both are
    saved but auto_review_required is forced True.

    Parameters
    ----------
    cover_only : bool
        If False (default) every message is returned including those where
        both models returned is_cover_request=False. If True, only messages
        where the primary result has is_cover_request=True are returned.
    """
    if claude_parser is None:
        claude_parser = NLPParser()
    if gemini_parser is None:
        gemini_parser = GeminiNLPParser()

    results = []
    for i, msg in enumerate(messages, 1):
        print(f"  [{i}/{len(messages)}] Parsing (dual): {msg.text[:60]}…")

        parse_kwargs = dict(
            message_text=msg.text,
            channel_name=msg.channel,
            message_date=msg.timestamp.date() if msg.timestamp else None,
            sender_name=msg.sender,
            is_reply=msg.is_reply,
            original_sender=msg.original_sender,
        )

        r_claude = claude_parser.parse(**parse_kwargs)
        r_gemini = gemini_parser.parse(**parse_kwargs)

        claude_failed = r_claude.parse_notes.startswith("API error:")
        gemini_failed = r_claude.parse_notes.startswith("Gemini API error:") or                         r_gemini.parse_notes.startswith("Gemini API error:")

        disparity = compute_disparity(r_claude, r_gemini)

        # Select primary result
        if gemini_failed and not claude_failed:
            primary, primary_src = r_claude, "anthropic"
        elif claude_failed and not gemini_failed:
            primary, primary_src = r_gemini, "gemini"
        elif r_gemini.confidence_score > r_claude.confidence_score:
            primary, primary_src = r_gemini, "gemini"
        else:
            primary, primary_src = r_claude, "anthropic"

        # Attach dual metadata to primary result
        primary.nlp_claude_type    = r_claude.message_type
        primary.nlp_gemini_type    = r_gemini.message_type
        primary.nlp_disparity_score = disparity
        primary.nlp_primary_source  = primary_src

        # High disparity → force manual review
        if disparity >= 0.35:
            primary.auto_review_required = True

        # Console summary
        status = "✓" if primary.is_cover_request else "─"
        agree  = "AGREE" if disparity < 0.20 else (f"DISPARITY={disparity:.2f}")
        print(
            f"    {status} Claude={r_claude.message_type}({r_claude.confidence_score:.2f})"
            f"  Gemini={r_gemini.message_type}({r_gemini.confidence_score:.2f})"
            f"  [{agree}]  primary={primary_src}"
        )
        if primary.parse_notes:
            print(f"    ─ Notes: {primary.parse_notes[:160]}")

        if cover_only and not primary.is_cover_request:
            continue
        results.append((msg, primary))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point (for testing a single message)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Test NLP parser on a single message")
    ap.add_argument("message", nargs="?", help="Message text to parse")
    ap.add_argument("--channel", default="", help="Channel name for context")
    args = ap.parse_args()

    if args.message:
        text = args.message
    else:
        # Interactive mode
        print("Enter message text (Ctrl+D / Ctrl+Z to finish):")
        lines = []
        try:
            while True:
                lines.append(input())
        except EOFError:
            pass
        text = "\n".join(lines)

    if not text.strip():
        print("No message provided.")
        sys.exit(1)

    print(f"\nParsing message: {text[:100]}")
    print(f'Channel: {args.channel or "(none)"}')
    print()

    p = NLPParser()
    r = p.parse(text, channel_name=args.channel)

    print("Result:")
    print(f"  is_cover_request:     {r.is_cover_request}")
    print(f"  message_type:         {r.message_type}")
    print(f"  confidence_score:     {r.confidence_score}")
    print(f"  teacher_name:         {r.teacher_name}")
    print(f"  class_date:           {r.class_date}")
    print(f"  class_time:           {r.class_time}")
    print(f"  studio:               {r.studio}")
    print(f"  discipline_code:      {r.discipline_code}")
    print(f"  estimated_class_count:{r.estimated_class_count}")
    print(f"  coverage_type:        {r.coverage_type}")
    print(f"  parse_notes:          {r.parse_notes}")


if __name__ == "__main__":
    main()
