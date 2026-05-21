"""
test_cover_processor_integration.py — Stage 2
==============================================
Integration tests for cover_processor.py, covering:

  1. Insert a message with coverage_type → verify payload sent to Supabase
  2. Insert a duplicate → verify deduplication (only 1 record written)
  3. Invalid coverage_type → verify insert is rejected before reaching Supabase
  4. Verify Supabase query payload contains correct coverage_type

All Supabase calls (sb_post, sb_get) are mocked so these tests run
without network access or live credentials.

Run:
    python -m pytest stage2/test_cover_processor_integration.py -v
  or:
    python stage2/test_cover_processor_integration.py
"""

import sys
import unittest
from datetime import datetime, date, time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from stage2.cover_processor import (
    insert_whatsapp_message,
    _message_fingerprint,
    load_recent_fingerprints,
)
from stage2.nlp_parser import ParseResult


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_msg(
    sender: str = "Sarah",
    text: str = "I need cover for my 6:15am Reformer class next Monday",
    timestamp: datetime | None = None,
    channel: str = "RITUAL REFORMER TEAM",
):
    """Build a minimal ChannelMessage-like mock."""
    msg = MagicMock()
    msg.sender = sender
    msg.text = text
    msg.timestamp = timestamp or datetime(2026, 4, 25, 6, 15, 0)
    msg.channel = channel
    msg._channel_db_id = "chan-001"
    msg.is_reply = False
    msg.original_sender = None
    return msg


def _make_request_result(
    teacher_name: str = "Sarah",
    class_date: date | None = None,
    coverage_type: str = "temporary",
    coverage_type_confidence: float = 0.95,
) -> ParseResult:
    """Build a ParseResult for a cover REQUEST."""
    r = ParseResult()
    r.is_cover_request = True
    r.message_type = "request"
    r.confidence_score = 0.90
    r.auto_review_required = False
    r.teacher_name = teacher_name
    r.class_date = class_date or date(2026, 4, 28)
    r.class_time = time(6, 15)
    r.studio = "Robina"
    r.discipline_code = "reformer"
    r.estimated_class_count = 1
    r.coverage_type = coverage_type
    r.coverage_type_confidence = coverage_type_confidence
    r.coverage_type_reasoning = "Message specifies next Monday — single date, temporary."
    r.parse_notes = "Clear request, high confidence."
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Test cases
# ─────────────────────────────────────────────────────────────────────────────

class TestInsertWithCoverageType(unittest.TestCase):
    """Test 1: Insert a message and verify coverage_type appears in the DB payload."""

    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    @patch("stage2.cover_processor.sb_post")
    def test_insert_stores_coverage_type(self, mock_post, mock_resolve):
        """coverage_type and coverage_type_confidence must be in the INSERT payload."""
        mock_post.return_value = [{"cover_request_id": "req-abc-001"}]

        msg = _make_msg()
        result = _make_request_result(coverage_type="temporary", coverage_type_confidence=0.95)
        existing_fps: set = set()

        ok = insert_whatsapp_message(msg, result, existing_fps, dry_run=False)

        self.assertTrue(ok, "Expected insert to succeed")
        self.assertEqual(mock_post.call_count, 1, "Expected exactly one Supabase insert")

        _, call_kwargs = mock_post.call_args
        # sb_post is called positionally: sb_post("cover_requests", payload)
        payload = mock_post.call_args[0][1]

        self.assertIn("coverage_type", payload, "coverage_type must be in INSERT payload")
        self.assertEqual(payload["coverage_type"], "temporary")

        self.assertIn("coverage_type_confidence", payload,
                      "coverage_type_confidence must be in INSERT payload")
        self.assertAlmostEqual(payload["coverage_type_confidence"], 0.95, places=2)

    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    @patch("stage2.cover_processor.sb_post")
    def test_insert_permanent_coverage_type(self, mock_post, mock_resolve):
        """Verify 'permanent' coverage_type flows through correctly."""
        mock_post.return_value = [{"cover_request_id": "req-abc-002"}]

        msg = _make_msg(text="I'm leaving — need someone to take my Tuesday classes permanently")
        result = _make_request_result(coverage_type="permanent", coverage_type_confidence=0.97)
        existing_fps: set = set()

        ok = insert_whatsapp_message(msg, result, existing_fps, dry_run=False)

        self.assertTrue(ok)
        payload = mock_post.call_args[0][1]
        self.assertEqual(payload["coverage_type"], "permanent")
        self.assertAlmostEqual(payload["coverage_type_confidence"], 0.97, places=2)

    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    @patch("stage2.cover_processor.sb_post")
    def test_insert_both_coverage_type(self, mock_post, mock_resolve):
        """Verify 'both' (default) coverage_type flows through correctly."""
        mock_post.return_value = [{"cover_request_id": "req-abc-003"}]

        msg = _make_msg(text="Can anyone cover my classes? Temporary or permanent, flexible.")
        result = _make_request_result(coverage_type="both", coverage_type_confidence=0.80)
        existing_fps: set = set()

        ok = insert_whatsapp_message(msg, result, existing_fps, dry_run=False)

        self.assertTrue(ok)
        payload = mock_post.call_args[0][1]
        self.assertEqual(payload["coverage_type"], "both")


class TestDeduplication(unittest.TestCase):
    """Test 2: Verify that inserting a duplicate message is blocked."""

    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    @patch("stage2.cover_processor.sb_post")
    def test_duplicate_is_skipped(self, mock_post, mock_resolve):
        """Second insert of the same message must be skipped; sb_post called only once."""
        mock_post.return_value = [{"cover_request_id": "req-dedup-001"}]

        msg = _make_msg()
        result = _make_request_result()
        existing_fps: set = set()

        # First insert — should succeed
        ok1 = insert_whatsapp_message(msg, result, existing_fps, dry_run=False)
        self.assertTrue(ok1, "First insert should succeed")

        # Second insert of the same message — should be deduped
        ok2 = insert_whatsapp_message(msg, result, existing_fps, dry_run=False)
        self.assertFalse(ok2, "Duplicate insert should return False")

        self.assertEqual(mock_post.call_count, 1,
                         "sb_post must be called exactly once — duplicate must not reach DB")

    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    @patch("stage2.cover_processor.sb_post")
    def test_different_coverage_type_same_message_still_deduped(self, mock_post, mock_resolve):
        """
        Even if coverage_type differs, the same sender/timestamp/text is still a duplicate.
        Deduplication key is (sender, timestamp, text[:120]) — NOT coverage_type.
        """
        mock_post.return_value = [{"cover_request_id": "req-dedup-002"}]

        msg = _make_msg()
        result_first = _make_request_result(coverage_type="temporary")
        existing_fps: set = set()

        ok1 = insert_whatsapp_message(msg, result_first, existing_fps, dry_run=False)
        self.assertTrue(ok1)

        # Same message, different coverage_type — still a duplicate
        result_second = _make_request_result(coverage_type="permanent")
        ok2 = insert_whatsapp_message(msg, result_second, existing_fps, dry_run=False)
        self.assertFalse(ok2, "Same message with different coverage_type must still be deduped")
        self.assertEqual(mock_post.call_count, 1)

    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    @patch("stage2.cover_processor.sb_post")
    def test_different_teacher_is_not_deduped(self, mock_post, mock_resolve):
        """
        Two messages from different teachers must both be inserted.
        Deduplication key includes teacher_name (from ParseResult), so distinct
        teachers with the same text/timestamp are NOT duplicates.
        """
        mock_post.side_effect = [
            [{"cover_request_id": "req-dedup-003"}],
            [{"cover_request_id": "req-dedup-004"}],
        ]

        msg1 = _make_msg(sender="Sarah", text="I need cover for my 6:15am class next Monday")
        msg2 = _make_msg(sender="Emma",  text="I need cover for my 6:15am class next Monday")

        # Different teacher names → different fingerprints even with same text/timestamp
        result1 = _make_request_result(teacher_name="Sarah")
        result2 = _make_request_result(teacher_name="Emma")
        existing_fps: set = set()

        ok1 = insert_whatsapp_message(msg1, result1, existing_fps, dry_run=False)
        ok2 = insert_whatsapp_message(msg2, result2, existing_fps, dry_run=False)

        self.assertTrue(ok1)
        self.assertTrue(ok2)
        self.assertEqual(mock_post.call_count, 2,
                         "Different teachers must produce two separate inserts")


class TestCoverageTypeValidation(unittest.TestCase):
    """Test 3: Verify that invalid coverage_type values are rejected before Supabase."""

    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    @patch("stage2.cover_processor.sb_post")
    def test_invalid_coverage_type_rejected(self, mock_post, mock_resolve):
        """An invalid coverage_type must cause insert to return False without calling sb_post."""
        msg = _make_msg()
        result = _make_request_result()
        result.coverage_type = "unknown_type"   # invalid — inject directly into ParseResult
        existing_fps: set = set()

        ok = insert_whatsapp_message(msg, result, existing_fps, dry_run=False)

        self.assertFalse(ok, "Invalid coverage_type must be rejected")
        mock_post.assert_not_called()

    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    @patch("stage2.cover_processor.sb_post")
    def test_empty_coverage_type_rejected(self, mock_post, mock_resolve):
        """An empty coverage_type string must also be rejected."""
        msg = _make_msg()
        result = _make_request_result()
        result.coverage_type = ""
        existing_fps: set = set()

        ok = insert_whatsapp_message(msg, result, existing_fps, dry_run=False)

        self.assertFalse(ok)
        mock_post.assert_not_called()

    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    @patch("stage2.cover_processor.sb_post")
    def test_all_valid_coverage_types_accepted(self, mock_post, mock_resolve):
        """All three valid coverage_types must pass validation."""
        mock_post.return_value = [{"cover_request_id": "req-val-001"}]

        for ct in ("temporary", "permanent", "both"):
            with self.subTest(coverage_type=ct):
                mock_post.reset_mock()
                msg = _make_msg(text=f"Cover request for {ct} coverage")
                result = _make_request_result(coverage_type=ct)
                existing_fps: set = set()

                ok = insert_whatsapp_message(msg, result, existing_fps, dry_run=False)

                self.assertTrue(ok, f"coverage_type='{ct}' must be accepted")
                mock_post.assert_called_once()


class TestSupabasePayloadContainsCoverageType(unittest.TestCase):
    """
    Test 4: Verify the exact Supabase INSERT payload for coverage_type fields.
    Simulates what the system would actually send to the database.
    """

    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    @patch("stage2.cover_processor.sb_post")
    def test_payload_fields_complete(self, mock_post, mock_resolve):
        """
        The INSERT payload must contain the expected coverage_type fields with correct values.
        This verifies the full chain: ParseResult → to_db_dict() → sb_post payload.
        """
        mock_post.return_value = [{"cover_request_id": "req-payload-001"}]

        msg = _make_msg(
            sender="Sarah",
            text="I need cover for my 6:15am Reformer class next Monday at Robina",
            timestamp=datetime(2026, 4, 21, 9, 0, 0),
        )
        result = _make_request_result(
            teacher_name="Sarah",
            class_date=date(2026, 4, 28),
            coverage_type="temporary",
            coverage_type_confidence=0.95,
        )
        existing_fps: set = set()

        ok = insert_whatsapp_message(msg, result, existing_fps, dry_run=False)
        self.assertTrue(ok)

        payload = mock_post.call_args[0][1]

        # Core fields
        self.assertEqual(payload["message_type"], "request")
        self.assertEqual(payload["requesting_teacher_name_raw"], "Sarah")
        self.assertEqual(payload["class_date"], "2026-04-28")

        # Coverage type fields — the focus of Phase 3
        self.assertEqual(payload["coverage_type"], "temporary",
                         "coverage_type must match the ParseResult value")
        self.assertAlmostEqual(payload["coverage_type_confidence"], 0.95, places=2,
                               msg="coverage_type_confidence must match the ParseResult value")

        # Ensure no invalid values slipped through
        self.assertIn(payload["coverage_type"], {"temporary", "permanent", "both"})
        self.assertGreaterEqual(payload["coverage_type_confidence"], 0.0)
        self.assertLessEqual(payload["coverage_type_confidence"], 1.0)

    @patch("stage2.cover_processor.resolve_teacher_id", return_value=None)
    @patch("stage2.cover_processor.sb_post")
    def test_dry_run_does_not_call_sb_post(self, mock_post, mock_resolve):
        """In dry-run mode, sb_post must not be called even with a valid payload."""
        msg = _make_msg()
        result = _make_request_result()
        existing_fps: set = set()

        ok = insert_whatsapp_message(msg, result, existing_fps, dry_run=True)

        self.assertTrue(ok, "dry_run should return True (would-insert)")
        mock_post.assert_not_called()


class TestFingerprintLogic(unittest.TestCase):
    """Unit tests for the deduplication fingerprint function itself."""

    def test_same_inputs_produce_same_fingerprint(self):
        sender = "Sarah"
        ts = datetime(2026, 4, 25, 6, 15, 0)
        text = "I need cover for my 6:15am class"
        fp1 = _message_fingerprint(sender, ts, text)
        fp2 = _message_fingerprint(sender, ts, text)
        self.assertEqual(fp1, fp2)

    def test_different_senders_produce_different_fingerprints(self):
        ts = datetime(2026, 4, 25, 6, 15, 0)
        text = "I need cover"
        fp1 = _message_fingerprint("Sarah", ts, text)
        fp2 = _message_fingerprint("Emma", ts, text)
        self.assertNotEqual(fp1, fp2)

    def test_sender_case_insensitive(self):
        """Fingerprint should be case-insensitive on sender."""
        ts = datetime(2026, 4, 25, 6, 15, 0)
        text = "I need cover"
        fp1 = _message_fingerprint("Sarah", ts, text)
        fp2 = _message_fingerprint("SARAH", ts, text)
        self.assertEqual(fp1, fp2, "Sender case must not affect fingerprint")

    def test_none_timestamp_handled(self):
        """Fingerprint must not raise if timestamp is None."""
        fp = _message_fingerprint("Sarah", None, "I need cover")
        self.assertIsInstance(fp, str)
        self.assertTrue(len(fp) > 0)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
