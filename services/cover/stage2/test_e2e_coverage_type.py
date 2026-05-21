"""
test_e2e_coverage_type.py — Stage 2
=====================================
End-to-end pipeline trace for coverage_type='temporary'.

Simulates the full path:
  WhatsApp message → NLP parser → cover_processor → database payload

All external calls (Claude API, Supabase) are mocked — no live network required.

Traces:
  1. A 'temporary' cover request flows through the full pipeline and
     produces a database payload with coverage_type='temporary'.
  2. A 'permanent' offer flows through and produces coverage_type='permanent'.
  3. An ambiguous message produces coverage_type='both'.

Run:
    python -m pytest stage2/test_e2e_coverage_type.py -v
"""

import json
import sys
import unittest
from datetime import datetime, date, time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from stage2.nlp_parser import NLPParser, ParseResult
from stage2.cover_processor import insert_whatsapp_message


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_whatsapp_message(
    sender: str = "Sarah",
    text: str = "I need cover for my 6:15am Reformer class next Monday",
    timestamp: datetime | None = None,
    channel: str = "RITUAL REFORMER TEAM",
    channel_db_id: str = "chan-e2e-001",
) -> MagicMock:
    """Simulate a ChannelMessage as returned by the WhatsApp monitor."""
    msg = MagicMock()
    msg.sender = sender
    msg.text = text
    msg.timestamp = timestamp or datetime(2026, 4, 25, 6, 0, 0)
    msg.channel = channel
    msg._channel_db_id = channel_db_id
    msg.is_reply = False
    msg.original_sender = None
    return msg


def _make_mock_parser_response(payload: dict) -> MagicMock:
    """Build a mock anthropic API response."""
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock()]
    mock_resp.content[0].text = json.dumps(payload)
    return mock_resp


def _parse_with_mock(message_text: str, claude_payload: dict, sender: str = "Sarah") -> ParseResult:
    """
    Create an NLPParser with an injected mock client and parse one message.
    No anthropic import, no network access.
    """
    parser = NLPParser()
    mock_client = MagicMock()
    parser._client = mock_client
    mock_client.messages.create.return_value = _make_mock_parser_response(claude_payload)
    return parser.parse(
        message_text,
        sender_name=sender,
        channel_name="RITUAL REFORMER TEAM",
        message_date=date(2026, 4, 25),
    )


# ─────────────────────────────────────────────────────────────────────────────
# E2E test cases
# ─────────────────────────────────────────────────────────────────────────────

class TestE2ECoverageTypePipeline(unittest.TestCase):
    """
    End-to-end trace: WhatsApp message → parser → processor → DB payload.
    Supabase and Claude are both mocked.
    """

    # ── Trace 1: temporary request ─────────────────────────────────────────

    @patch("stage2.cover_processor.sb_post")
    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    def test_temporary_request_flows_through_pipeline(self, _mock_resolve, mock_sb_post):
        """
        Pipeline trace: 'next Monday' request → coverage_type='temporary' stored.

        Stages verified:
          ✓ NLP parser classifies coverage_type='temporary'
          ✓ cover_processor.insert_whatsapp_message() accepts the record
          ✓ Supabase payload contains coverage_type='temporary'
          ✓ Supabase payload contains coverage_type_confidence >= 0.8
        """
        message_text = "I need cover for my 6:15am Reformer class next Monday ASAP"
        msg = _make_whatsapp_message(sender="Sarah", text=message_text)

        # Stage 1: NLP parser (Claude mocked)
        claude_payload = {
            "message_type": "request",
            "is_cover_request": True,
            "confidence_score": 0.93,
            "auto_review_required": False,
            "teacher_name": "Sarah",
            "class_date_iso": "2026-04-28",
            "class_time_iso": "06:15:00",
            "class_times_iso": ["06:15:00"],
            "studios": ["Robina"],
            "discipline_codes": ["reformer"],
            "estimated_class_count": 1,
            "coverage_type": "temporary",
            "coverage_type_confidence": 0.95,
            "coverage_type_reasoning": "Signal: 'next Monday', 'ASAP' — single date, one-off.",
            "parse_notes": "Clear request, temporary signals present.",
        }
        result = _parse_with_mock(message_text, claude_payload, sender="Sarah")

        # Verify Stage 1: parser output
        self.assertEqual(result.message_type, "request")
        self.assertEqual(result.coverage_type, "temporary")
        self.assertGreaterEqual(result.coverage_type_confidence, 0.8)
        self.assertIsNotNone(result.coverage_type_reasoning)

        # Stage 2: cover_processor → database
        mock_sb_post.return_value = [{"cover_request_id": "msg-e2e-001"}]
        existing_fps: set = set()
        inserted = insert_whatsapp_message(msg, result, existing_fps, dry_run=False)

        # Verify Stage 2: insertion succeeded
        self.assertTrue(inserted, "insert_whatsapp_message() should return True")
        mock_sb_post.assert_called_once()

        # Verify Stage 3: database payload contents
        actual_payload = mock_sb_post.call_args[0][1]  # second positional arg
        self.assertEqual(actual_payload.get("coverage_type"), "temporary",
                         f"Expected 'temporary', got {actual_payload.get('coverage_type')!r}")
        self.assertAlmostEqual(actual_payload.get("coverage_type_confidence"), 0.95, places=2)
        self.assertNotIn("coverage_type_reasoning", actual_payload,
                         "coverage_type_reasoning must NOT be stored in the database")
        self.assertEqual(actual_payload.get("message_type"), "request")

    # ── Trace 2: permanent offer ───────────────────────────────────────────

    @patch("stage2.cover_processor.sb_post")
    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    def test_permanent_offer_flows_through_pipeline(self, _mock_resolve, mock_sb_post):
        """
        Pipeline trace: 'take over permanently' offer → coverage_type='permanent' stored.
        """
        message_text = "I can take over Sarah's Tuesday classes permanently from May"
        msg = _make_whatsapp_message(sender="Emma", text=message_text)

        claude_payload = {
            "message_type": "offer",
            "is_cover_request": True,
            "confidence_score": 0.91,
            "auto_review_required": False,
            "offering_teacher_name": "Emma",
            "offered_dates_iso": [],
            "offered_times_iso": [],
            "offered_studios": ["Robina"],
            "offered_disciplines": ["reformer"],
            "can_cover_count": "?",
            "coverage_type": "permanent",
            "coverage_type_confidence": 0.97,
            "coverage_type_reasoning": "Signal: 'permanently', 'take over' — clear permanent offer.",
            "parse_notes": "Clear permanent offer.",
        }
        result = _parse_with_mock(message_text, claude_payload, sender="Emma")

        self.assertEqual(result.message_type, "offer")
        self.assertEqual(result.coverage_type, "permanent")
        self.assertGreaterEqual(result.coverage_type_confidence, 0.8)

        mock_sb_post.return_value = [{"cover_request_id": "msg-e2e-002"}]
        inserted = insert_whatsapp_message(msg, result, set(), dry_run=False)

        self.assertTrue(inserted)
        actual_payload = mock_sb_post.call_args[0][1]
        self.assertEqual(actual_payload.get("coverage_type"), "permanent")
        self.assertNotIn("coverage_type_reasoning", actual_payload)

    # ── Trace 3: ambiguous → both ──────────────────────────────────────────

    @patch("stage2.cover_processor.sb_post")
    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    def test_ambiguous_message_defaults_to_both(self, _mock_resolve, mock_sb_post):
        """
        Pipeline trace: no coverage signal → coverage_type='both' (safe default).
        """
        message_text = "Can anyone help with my Tuesday class?"
        msg = _make_whatsapp_message(sender="Tom", text=message_text)

        claude_payload = {
            "message_type": "request",
            "is_cover_request": True,
            "confidence_score": 0.75,
            "auto_review_required": True,
            "teacher_name": "Tom",
            "class_date_iso": None,
            "class_time_iso": None,
            "class_times_iso": [],
            "studios": [],
            "discipline_codes": [],
            "estimated_class_count": 1,
            "coverage_type": "both",
            "coverage_type_confidence": 0.50,
            "coverage_type_reasoning": "No duration signals found — defaulting to 'both'.",
            "parse_notes": "Ambiguous request.",
        }
        result = _parse_with_mock(message_text, claude_payload, sender="Tom")

        self.assertEqual(result.coverage_type, "both")

        mock_sb_post.return_value = [{"cover_request_id": "msg-e2e-003"}]
        inserted = insert_whatsapp_message(msg, result, set(), dry_run=False)

        self.assertTrue(inserted)
        actual_payload = mock_sb_post.call_args[0][1]
        self.assertEqual(actual_payload.get("coverage_type"), "both")

    # ── Trace 4: deduplication unaffected ─────────────────────────────────

    @patch("stage2.cover_processor.sb_post")
    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    def test_deduplication_unaffected_by_coverage_type(self, _mock_resolve, mock_sb_post):
        """
        The same message inserted twice must be deduplicated (only 1 DB write).
        Different coverage_type values do NOT bypass deduplication.
        """
        msg = _make_whatsapp_message(
            sender="Sarah",
            text="I need cover for my 6:15am Reformer class next Monday",
            timestamp=datetime(2026, 4, 25, 6, 0, 0),
        )
        claude_payload = {
            "message_type": "request",
            "is_cover_request": True,
            "confidence_score": 0.90,
            "auto_review_required": False,
            "teacher_name": "Sarah",
            "class_date_iso": "2026-04-28",
            "class_time_iso": "06:15:00",
            "class_times_iso": ["06:15:00"],
            "studios": ["Robina"],
            "discipline_codes": ["reformer"],
            "estimated_class_count": 1,
            "coverage_type": "temporary",
            "coverage_type_confidence": 0.90,
            "coverage_type_reasoning": "Single date signal.",
            "parse_notes": "",
        }
        result = _parse_with_mock(msg.text, claude_payload)

        mock_sb_post.return_value = [{"cover_request_id": "msg-e2e-004"}]
        existing_fps: set = set()

        # First insert: should succeed
        first = insert_whatsapp_message(msg, result, existing_fps, dry_run=False)
        self.assertTrue(first)
        self.assertEqual(mock_sb_post.call_count, 1)

        # Second insert (same message): should be skipped
        result2 = _parse_with_mock(msg.text, {**claude_payload, "coverage_type": "permanent"})
        second = insert_whatsapp_message(msg, result2, existing_fps, dry_run=False)
        self.assertFalse(second, "Duplicate should be rejected regardless of coverage_type")
        self.assertEqual(mock_sb_post.call_count, 1, "Supabase should only be called once")

    # ── Trace 5: invalid coverage_type from LLM is rejected ───────────────

    @patch("stage2.cover_processor.sb_post")
    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    def test_invalid_coverage_type_rejected_before_db(self, _mock_resolve, mock_sb_post):
        """
        If NLP parser somehow lets an invalid coverage_type through (e.g. 'once-off'),
        cover_processor must reject the insert before reaching Supabase.

        Note: The parser normalises invalid values to 'both', so this tests the
        processor's own validation as a defence-in-depth layer.
        """
        msg = _make_whatsapp_message()

        # Manually build a ParseResult with an invalid coverage_type
        result = ParseResult()
        result.is_cover_request = True
        result.message_type = "request"
        result.confidence_score = 0.85
        result.auto_review_required = False
        result.teacher_name = "Sarah"
        result.class_date = date(2026, 4, 28)
        result.class_time = time(6, 15)
        result.studio = "Robina"
        result.discipline_code = "reformer"
        result.coverage_type = "once-off"   # intentionally invalid
        result.coverage_type_confidence = 0.80

        inserted = insert_whatsapp_message(msg, result, set(), dry_run=False)

        self.assertFalse(inserted, "Invalid coverage_type should cause insert to return False")
        mock_sb_post.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
