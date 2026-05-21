"""
test_api_keys.py
----------------
Smoke-test for the Anthropic (Claude) and Google Gemini API keys.

Runs a sample cover-request message through both parsers using the same
code path as the production cover_processor / nlp_parser stack.

Usage:
    python test_api_keys.py

Exit codes:
    0  all checks passed
    1  one or more checks failed
"""

import sys
import time
from pathlib import Path

# Allow imports from project root and stage2/
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "stage2"))

# Load config (.env always overrides system env vars via override=True in config.py)
from config import (
    ANTHROPIC_API_KEY,
    NLP_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
)

SAMPLE_MSG = (
    "Hi everyone, I need cover for my Reformer class at Robina this Saturday "
    "28 June at 9am. I'm unable to teach due to illness. Thanks, Sam"
)
CHANNEL = "RITUAL YIN"

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
WARN = "\033[33mWARN\033[0m"

failures = 0


def check(label, ok, detail=""):
    global failures
    status = PASS if ok else FAIL
    print("  [" + status + "] " + label + (" -- " + detail if detail else ""))
    if not ok:
        failures += 1


# =============================================================================
# 1. Config sanity checks
# =============================================================================
print("\n=== 1. Config ===")
check("ANTHROPIC_API_KEY set", bool(ANTHROPIC_API_KEY),
      "key=" + ("***" + ANTHROPIC_API_KEY[-4:] if ANTHROPIC_API_KEY else "MISSING"))
check("GEMINI_API_KEY set", bool(GEMINI_API_KEY),
      "key=" + ("***" + GEMINI_API_KEY[-4:] if GEMINI_API_KEY else "MISSING"))
check("NLP_MODEL",    bool(NLP_MODEL),    NLP_MODEL)
check("GEMINI_MODEL", bool(GEMINI_MODEL), GEMINI_MODEL)

# =============================================================================
# 2. Direct Anthropic API call
# =============================================================================
print("\n=== 2. Anthropic API (direct) ===")
try:
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    t0 = time.time()
    resp = client.messages.create(
        model=NLP_MODEL,
        max_tokens=64,
        messages=[{"role": "user", "content": "Reply with exactly: OK"}],
    )
    elapsed = time.time() - t0
    reply = resp.content[0].text.strip() if resp.content else ""
    check("API call succeeded",  True,       str(round(elapsed, 2)) + "s")
    check("Response non-empty",  bool(reply), repr(reply))
    check("Model in response",   bool(resp.model), "returned model=" + resp.model)
except Exception as exc:
    check("API call succeeded", False, str(exc))

# =============================================================================
# 3. Direct Gemini API call  (uses google-genai, same as nlp_parser.py)
# =============================================================================
print("\n=== 3. Gemini API (direct) ===")
try:
    from google import genai as _genai
    from google.genai import types as _genai_types
    gclient_direct = _genai.Client(api_key=GEMINI_API_KEY)
    t0 = time.time()
    resp_g = gclient_direct.models.generate_content(
        model=GEMINI_MODEL,
        contents="Reply with exactly: OK",
        config=_genai_types.GenerateContentConfig(temperature=0.0),
    )
    elapsed = time.time() - t0
    reply_g = resp_g.text.strip() if resp_g.text else ""
    check("API call succeeded",  True,        str(round(elapsed, 2)) + "s")
    check("Response non-empty",  bool(reply_g), repr(reply_g))
except Exception as exc:
    check("API call succeeded", False, str(exc))

# =============================================================================
# 4. Full NLP parse -- Claude (NLPParser)
# =============================================================================
print("\n=== 4. NLP parse -- Claude (NLPParser) ===")
print('  Message: "' + SAMPLE_MSG[:70] + '..."')
result = None
try:
    from nlp_parser import NLPParser
    parser = NLPParser()
    t0 = time.time()
    result = parser.parse(SAMPLE_MSG, channel_name=CHANNEL)
    elapsed = time.time() - t0
    check("Parse completed",          True, str(round(elapsed, 2)) + "s")
    check("message_type = 'request'", result.message_type == "request",
          "got '" + result.message_type + "'")
    check("confidence > 0",           result.confidence_score > 0,
          str(round(result.confidence_score, 2)))
    notes_lower = (result.parse_notes or "").lower()
    check("No API error in notes",
          "credit balance" not in notes_lower and "api error" not in notes_lower,
          (result.parse_notes or "")[:80])
    check("teacher_name extracted",   bool(result.teacher_name),
          repr(result.teacher_name))
    check("class_date extracted",     result.class_date is not None,
          str(result.class_date))
except Exception as exc:
    check("Parse completed", False, str(exc))

# =============================================================================
# 5. Full NLP parse -- Gemini (GeminiNLPParser)
# =============================================================================
print("\n=== 5. NLP parse -- Gemini (GeminiNLPParser) ===")
gresult = None
try:
    from nlp_parser import GeminiNLPParser
    gparser = GeminiNLPParser()
    t0 = time.time()
    gresult = gparser.parse(SAMPLE_MSG, channel_name=CHANNEL)
    elapsed = time.time() - t0
    check("Parse completed",          True, str(round(elapsed, 2)) + "s")
    check("message_type = 'request'", gresult.message_type == "request",
          "got '" + gresult.message_type + "'")
    check("confidence > 0",           gresult.confidence_score > 0,
          str(round(gresult.confidence_score, 2)))
    gnotes_lower = (gresult.parse_notes or "").lower()
    check("No API error in notes",
          "api error" not in gnotes_lower,
          (gresult.parse_notes or "")[:80])
except Exception as exc:
    check("Parse completed", False, str(exc))

# =============================================================================
# 6. Model agreement check
# =============================================================================
print("\n=== 6. Model agreement ===")
if result is not None and gresult is not None:
    claude_type = result.message_type
    gemini_type = gresult.message_type
    agreement   = claude_type == gemini_type
    tag = PASS if agreement else WARN
    print("  [" + tag + "] Claude=" + claude_type + "  Gemini=" + gemini_type +
          "  " + ("(agree)" if agreement else "(DISAGREE -- auto_review will be set)"))
else:
    print("  [" + WARN + "] Skipped -- one or both parsers failed above")

# =============================================================================
# Summary
# =============================================================================
print()
print("=" * 54)
if failures == 0:
    print("  [" + PASS + "] All checks passed.")
else:
    print("  [" + FAIL + "] " + str(failures) + " check(s) failed -- see above.")
print("=" * 54)
print()

sys.exit(0 if failures == 0 else 1)
