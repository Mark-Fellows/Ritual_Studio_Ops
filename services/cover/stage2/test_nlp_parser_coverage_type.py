"""
test_nlp_parser_coverage_type.py — Stage 2
===========================================
Unit tests for coverage_type classification in nlp_parser.py.

All Claude API calls are mocked — no network access or credentials required.

Tests:
  1. Temporary-indicator message → coverage_type='temporary'
  2. Permanent-indicator message → coverage_type='permanent'
  3. Flexible/both message → coverage_type='both'
  4. Ambiguous message (no signals) → coverage_type='both' (safe default)
  5. Invalid coverage_type in response → falls back to 'both'
  6. Coverage type extracted for REQUEST messages
  7. Coverage type extracted for OFFER messages
  8. Coverage type extracted for REJECTION messages
  9. Confidence clamped to [0.0, 1.0]
  10. coverage_type_reasoning NOT in to_db_dict()

Run:
    python -m pytest stage2/test_nlp_parser_coverage_type.py -v
  or:
    python stage2/test_nlp_parser_coverage_type.py
"""

import json
import sys
import unittest
from datetime import date, time, datetime
from pathlib import Path
from unittest.mock import MagicMock

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from stage2.nlp_parser import NLPParser, ParseResult


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_claude_response(payload: dict) -> MagicMock:
    """
    Build a mock that looks like anthropic.messages.create() returns.
    The parser reads response.content[0].text.
    """
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = json.dumps(payload)
    return mock_response


def _base_request_payload(**overrides) -> dict:
    """Minimal valid Claude response for a REQUEST message."""
    payload = {
        "message_type": "request",
        "is_cover_request": True,
        "confidence_score": 0.92,
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
        "coverage_type_reasoning": "Message says 'next Monday' — single date, temporary.",
        "parse_notes": "Clear request.",
    }
    payload.update(overrides)
    return payload


def _base_offer_payload(**overrides) -> dict:
    """Minimal valid Claude response for an OFFER message."""
    payload = {
        "message_type": "offer",
        "is_cover_request": True,
        "confidence_score": 0.88,
        "auto_review_required": False,
        "offering_teacher_name": "Emma",
        "offered_dates_iso": ["2026-04-28"],
        "offered_times_iso": ["06:15:00"],
        "offered_studios": ["Robina"],
        "offered_disciplines": ["reformer"],
        "can_cover_count": 1,
        "coverage_type": "temporary",
        "coverage_type_confidence": 0.90,
        "coverage_type_reasoning": "Explicitly said 'just this Monday'.",
        "parse_notes": "Clear offer.",
    }
    payload.update(overrides)
    return payload


def _base_rejection_payload(**overrides) -> dict:
    """Minimal valid Claude response for a REJECTION message."""
    payload = {
        "message_type": "rejection",
        "is_cover_request": True,
        "confidence_score": 0.85,
        "auto_review_required": False,
        "declining_teacher_name": "Tom",
        "declining_for_whom": "Sarah",
        "rejection_reason": "Away that day",
        "coverage_type": "both",
        "coverage_type_confidence": 0.70,
        "coverage_type_reasoning": "Rejection — coverage type not specified.",
        "parse_notes": "Clear rejection.",
    }
    payload.update(overrides)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# Test class
# ─────────────────────────────────────────────────────────────────────────────

class TestCoverageTypeClassification(unittest.TestCase):
    """Tests that the NLP parser correctly extracts coverage_type."""

    def setUp(self):
        """Create an NLPParser and inject a mock Anthropic client.

        NLPParser imports anthropic lazily inside _get_client(), so we can
        instantiate NLPParser without any real credentials and then set
        self.parser._client directly — _get_client() skips the import when
        _client is already set.
        """
        # NLPParser.__init__ does NOT call anthropic — safe to instantiate.
        self.parser = NLPParser()
        # Inject mock so _get_client() returns it without touching the network.
        self.mock_client = MagicMock()
        self.parser._client = self.mock_client

    def _parse(self, message: str, payload: dict, sender: str = "TestTeacher") -> ParseResult:
        """Helper: set mock response and call parse()."""
        self.mock_client.messages.create.return_value = _mock_claude_response(payload)
        return self.parser.parse(message, sender_name=sender, channel_name="RITUAL REFORMER TEAM")

    # ─── Classification accuracy ──────────────────────────────────────────────

    def test_temporary_indicator_classified_as_temporary(self):
        """'I need cover next Monday' → coverage_type='temporary'"""
        result = self._parse(
            "I need cover for my 6:15am Reformer class next Monday",
            _base_request_payload(coverage_type="temporary", coverage_type_confidence=0.95),
        )
        self.assertEqual(result.coverage_type, "temporary")
        self.assertGreaterEqual(result.coverage_type_confidence, 0.8)

    def test_permanent_indicator_classified_as_permanent(self):
        """'Looking for a permanent replacement' → coverage_type='permanent'"""
        result = self._parse(
            "I'm leaving and need someone to take over my Tuesday classes permanently",
            _base_request_payload(coverage_type="permanent", coverage_type_confidence=0.97),
        )
        self.assertEqual(result.coverage_type, "permanent")
        self.assertGreaterEqual(result.coverage_type_confidence, 0.8)

    def test_flexible_indicator_classified_as_both(self):
        """'Can do temporary or permanent, flexible' → coverage_type='both'"""
        result = self._parse(
            "Happy to cover — either one-off or take it on permanently, flexible",
            _base_offer_payload(coverage_type="both", coverage_type_confidence=0.88),
        )
        self.assertEqual(result.coverage_type, "both")
        self.assertGreaterEqual(result.coverage_type_confidence, 0.8)

    def test_ambiguous_message_defaults_to_both(self):
        """Message with no coverage signals → coverage_type='both' (safe default)."""
        result = self._parse(
            "Can anyone help with my class?",
            _base_request_payload(coverage_type="both", coverage_type_confidence=0.50),
        )
        self.assertEqual(result.coverage_type, "both")

    # ─── Invalid / missing values from LLM ───────────────────────────────────

    def test_invalid_coverage_type_in_response_falls_back_to_both(self):
        """LLM returns an unrecognised value → parser falls back to 'both'."""
        result = self._parse(
            "I need someone to cover",
            _base_request_payload(coverage_type="unknown_value"),
        )
        self.assertEqual(result.coverage_type, "both")

    def test_missing_coverage_type_in_response_defaults_to_both(self):
        """LLM omits coverage_type field entirely → defaults to 'both'."""
        payload = _base_request_payload()
        del payload["coverage_type"]
        result = self._parse("I need cover", payload)
        self.assertEqual(result.coverage_type, "both")

    def test_missing_confidence_in_response_defaults_to_1_0(self):
        """LLM omits coverage_type_confidence → defaults to 1.0."""
        payload = _base_request_payload()
        del payload["coverage_type_confidence"]
        result = self._parse("I need temporary cover", payload)
        self.assertEqual(result.coverage_type_confidence, 1.0)

    # ─── Confidence clamping ─────────────────────────────────────────────────

    def test_confidence_clamped_above_1(self):
        """Confidence value > 1.0 is clamped to 1.0."""
        result = self._parse(
            "I need temporary cover",
            _base_request_payload(coverage_type_confidence=1.5),
        )
        self.assertLessEqual(result.coverage_type_confidence, 1.0)

    def test_confidence_clamped_below_0(self):
        """Confidence value < 0.0 is clamped to 0.0."""
        result = self._parse(
            "I need temporary cover",
            _base_request_payload(coverage_type_confidence=-0.5),
        )
        self.assertGreaterEqual(result.coverage_type_confidence, 0.0)

    # ─── All three message types receive coverage_type ───────────────────────

    def test_request_message_extracts_coverage_type(self):
        """REQUEST messages include coverage_type extraction."""
        result = self._parse(
            "I need cover for my class next Monday",
            _base_request_payload(coverage_type="temporary"),
        )
        self.assertEqual(result.message_type, "request")
        self.assertEqual(result.coverage_type, "temporary")

    def test_offer_message_extracts_coverage_type(self):
        """OFFER messages include coverage_type extraction."""
        result = self._parse(
            "I can cover next Monday only",
            _base_offer_payload(coverage_type="temporary", coverage_type_confidence=0.90),
        )
        self.assertEqual(result.message_type, "offer")
        self.assertEqual(result.coverage_type, "temporary")

    def test_rejection_message_extracts_coverage_type(self):
        """REJECTION messages include coverage_type extraction."""
        result = self._parse(
            "Sorry, I can't help on Monday",
            _base_rejection_payload(coverage_type="both", coverage_type_confidence=0.70),
        )
        self.assertEqual(result.message_type, "rejection")
        self.assertEqual(result.coverage_type, "both")

    # ─── to_db_dict() serialisation ──────────────────────────────────────────

    def test_coverage_type_present_in_db_dict(self):
        """coverage_type and coverage_type_confidence appear in to_db_dict()."""
        result = self._parse(
            "I need temporary cover next Monday",
            _base_request_payload(coverage_type="temporary", coverage_type_confidence=0.95),
        )
        db_dict = result.to_db_dict(
            channel_db_id="chan-001",
            raw_message="I need temporary cover next Monday",
            message_timestamp=datetime(2026, 4, 25, 9, 0, 0),
        )
        self.assertIn("coverage_type", db_dict)
        self.assertIn("coverage_type_confidence", db_dict)
        self.assertEqual(db_dict["coverage_type"], "temporary")
        self.assertAlmostEqual(db_dict["coverage_type_confidence"], 0.95, places=2)

    def test_coverage_type_reasoning_excluded_from_db_dict(self):
        """coverage_type_reasoning must NOT appear in to_db_dict() (diagnostic only)."""
        result = self._parse(
            "I need temporary cover next Monday",
            _base_request_payload(
                coverage_type="temporary",
                coverage_type_reasoning="Signal: 'next Monday'.",
            ),
        )
        db_dict = result.to_db_dict(
            channel_db_id="chan-001",
            raw_message="I need temporary cover next Monday",
            message_timestamp=datetime(2026, 4, 25, 9, 0, 0),
        )
        self.assertNotIn("coverage_type_reasoning", db_dict)

    def test_coverage_type_reasoning_accessible_on_result(self):
        """coverage_type_reasoning IS accessible on the ParseResult object."""
        result = self._parse(
            "I need temporary cover next Monday",
            _base_request_payload(
                coverage_type="temporary",
                coverage_type_reasoning="Signal: 'next Monday'.",
            ),
        )
        self.assertEqual(result.coverage_type_reasoning, "Signal: 'next Monday'.")

    # ─── Regression: existing fields unaffected ───────────────────────────────

    def test_message_type_still_extracted(self):
        """Adding coverage_type fields does not break message_type extraction."""
        result = self._parse(
            "I need cover for my 6:15am Reformer class next Monday",
            _base_request_payload(),
        )
        self.assertEqual(result.message_type, "request")
        self.assertTrue(result.is_cover_request)

    def test_teacher_name_still_extracted(self):
        """teacher_name still extracted alongside coverage_type."""
        result = self._parse(
            "I need cover for my 6:15am Reformer class next Monday",
            _base_request_payload(coverage_type="temporary"),
        )
        self.assertEqual(result.teacher_name, "Sarah")

    def test_confidence_score_still_extracted(self):
        """Overall confidence_score still extracted (separate from coverage_type_confidence)."""
        result = self._parse(
            "I need cover for my 6:15am Reformer class next Monday",
            _base_request_payload(confidence_score=0.92),
        )
        self.assertAlmostEqual(result.confidence_score, 0.92, places=2)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
