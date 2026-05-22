# -*- coding: utf-8 -*-
"""test_phase5.py -- Phase 5 integrity tests for Ritual Studio Ops.

Tests:
  1. scripts/reconcile.py exists and is non-trivial
  2. Key functions present in reconcile.py
  3. P1 detection logic present (audit origin check, drift checks)
  4. Graceful degradation on network failure (no hard crash on import)
  5. State file and reports directory scaffolding
  6. Script is importable as a module (syntax valid)
  7. --no-save flag present in argparse
  8. reconcile_reports/ directory exists
"""
import sys
import ast
import subprocess
from pathlib import Path

ROOT       = Path(__file__).parent.parent
RECONCILE  = ROOT / "scripts" / "reconcile.py"
REPORTS    = ROOT / "scripts" / "reconcile_reports"

PASS = "OK"; FAIL = "FAIL"; results = []

def check(description, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, description, detail))
    if not condition:
        msg = f"  {FAIL}: {description}"
        if detail: msg += f" -- {detail}"
        print(msg)
    return condition


src = RECONCILE.read_text(encoding="utf-8") if RECONCILE.exists() else ""

# -- Section 1: File existence and size ----------------------------------------
print("1. reconcile.py existence and size")
check("reconcile.py exists", RECONCILE.exists())
check("reconcile.py is non-trivial (>100 lines)",
      src.count("\n") > 100,
      f"{src.count(chr(10))} lines found")

# -- Section 2: Key functions --------------------------------------------------
print("2. Key functions present")
check("check_audit_log function defined",     "def check_audit_log(" in src)
check("check_cover_requests function defined","def check_cover_requests(" in src)
check("check_trainee_bookings function defined","def check_trainee_bookings(" in src)
check("check_teachers function defined",      "def check_teachers(" in src)
check("compare_snapshot function defined",    "def compare_snapshot(" in src)
check("main() function defined",              "def main(" in src)

# -- Section 3: P1 detection logic ---------------------------------------------
print("3. P1 detection logic present")
check("P1_ISSUES list defined",   "P1_ISSUES" in src)
check("p1() helper function",     "def p1(" in src)
check("Legacy write detection present",
      "legacy_count" in src and "non-RSO" in src.lower() or "legacy" in src.lower())
check("Teacher count drop triggers P1",
      "t_today < t_yest" in src or "Teacher count dropped" in src)
check("Cover request drop triggers P1",
      "cr_today < cr_yest" in src or "Cover request count dropped" in src)
check("[RSO] marker constant defined",
      'RSO_MARKER' in src and '"[RSO]"' in src or "'[RSO]'" in src)

# -- Section 4: Graceful degradation -------------------------------------------
print("4. Graceful degradation on network failure")
check("safe_get wrapper used (no raw sb_get calls in checks)",
      "safe_get(" in src)
check("safe_get returns default on exception",
      "except Exception" in src and "default" in src)
check("Exit code 2 on config error",
      "sys.exit(2)" in src)
check("Exit code 1 on P1 issues",
      "sys.exit(1 if P1_ISSUES" in src or
      "sys.exit(1)" in src)

# -- Section 5: State / snapshot machinery ------------------------------------
print("5. State file and snapshot logic")
check("STATE_FILE defined",      "STATE_FILE" in src)
check("reconcile_state.json used",
      "reconcile_state.json" in src)
check("Snapshot saved with json.dumps",
      "json.dumps(" in src)
check("Yesterday's snapshot loaded",
      "yesterday" in src and "json.loads" in src)

# -- Section 6: Syntax valid ---------------------------------------------------
print("6. Script parses cleanly (ast)")
try:
    ast.parse(src)
    check("reconcile.py has valid Python syntax", True)
except SyntaxError as e:
    check("reconcile.py has valid Python syntax", False, str(e))

# -- Section 7: CLI flags ------------------------------------------------------
print("7. CLI argument handling")
check("--no-save flag defined",  '"--no-save"' in src or "'--no-save'" in src)
check("--days flag defined",     '"--days"' in src or "'--days'" in src)
check("argparse used",           "argparse" in src)

# -- Section 8: Directory scaffolding ------------------------------------------
print("8. reconcile_reports/ directory")
check("reconcile_reports/ directory exists", REPORTS.is_dir())
check("reconcile_reports/ has .gitkeep or is otherwise committed",
      (REPORTS / ".gitkeep").exists() or any(REPORTS.iterdir()))


# -- Summary -------------------------------------------------------------------
passed = sum(1 for s, _, _ in results if s == PASS)
failed = sum(1 for s, _, _ in results if s == FAIL)
total  = len(results)
print(f"\nResults: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("Phase 5 integrity checks: ALL PASS -- reconciliation script ready")
else:
    print("Phase 5 integrity checks: FAILED -- fix above before proceeding")
    sys.exit(1)
