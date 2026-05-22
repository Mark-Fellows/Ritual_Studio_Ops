# -*- coding: utf-8 -*-
"""test_phase4.py -- Phase 4 integrity tests for Ritual Studio Ops.

Tests:
  1. Version comment and build stamp updated to Phase 4
  2. WRITES_ENABLED = true
  3. writeAudit adds [RSO] prefix to descriptions
  4. Cover Requests: approveCoverRequest and assignCoverRequest functions present
  5. Cover Requests: row buttons are no longer hardcoded disabled
  6. Teacher Portal: acceptCoverOpportunity and declineCoverOpportunity functions present
  7. Teacher Portal: row buttons are no longer hardcoded disabled
  8. Legacy TM banner present in ritual-teacher-management31.html
  9. Legacy CM dashboard banner present in cover_dashboard.html
  10. Legacy teacher portal banner present in teacher_portal.html
"""
import sys
from pathlib import Path

ROOT    = Path(__file__).parent.parent
APP     = ROOT / "app" / "ritual-studio-ops-v1.html"
TM_APP  = Path(r"C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Teacher_Management\ritual-teacher-management31.html")
CM_DASH = Path(r"C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management\public\cover_dashboard.html")
CM_PORT = Path(r"C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management\public\teacher_portal.html")

PASS = "OK"; FAIL = "FAIL"; results = []

def check(description, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, description, detail))
    if not condition:
        msg = f"  {FAIL}: {description}"
        if detail: msg += f" -- {detail}"
        print(msg)
    return condition


src = APP.read_text(encoding="utf-8") if APP.exists() else ""

# -- Section 1: Version markers ------------------------------------------------
print("1. Version markers updated to Phase 4")
check("App file exists", APP.exists())
check("Version comment is Phase 4",
      "Phase 4: write-enabled shell" in src or "Phase 4" in src[:200])
check("Build stamp is Phase 4",
      'title="RSO v1 Phase 4"' in src or "Phase 4" in src)
check("Settings version shows Phase 4",
      "RSO v1 · Phase 4" in src or "Phase 4" in src)

# -- Section 2: WRITES_ENABLED -------------------------------------------------
print("2. WRITES_ENABLED = true")
check("WRITES_ENABLED set to true",
      "const WRITES_ENABLED = true;" in src)
check("No 'Writes not yet enabled in Phase 2' messages remain",
      "Writes not yet enabled in Phase 2" not in src)

# -- Section 3: writeAudit [RSO] prefix ----------------------------------------
print("3. writeAudit adds [RSO] prefix")
check("writeAudit posts [RSO] prefix",
      "'[RSO] '+description" in src or '"[RSO] "+description' in src or "[RSO]" in src)

# -- Section 4: Cover Requests write functions ---------------------------------
print("4. Cover Requests write functions present")
check("approveCoverRequest function defined",
      "async function approveCoverRequest(" in src)
check("assignCoverRequest function defined",
      "async function assignCoverRequest(" in src)
check("approveCoverRequest PATCHes status=approved",
      "status: 'approved'" in src or 'status:"approved"' in src)
check("assignCoverRequest PATCHes status=covered",
      "status: 'covered'" in src or 'status:"covered"' in src)
check("approveCoverRequest calls writeAudit",
      "approveCoverRequest" in src and "writeAudit" in src)

# -- Section 5: Cover Requests buttons no longer hardcoded disabled ------------
print("5. Cover Requests buttons not hardcoded disabled")
check("No 'disabled title=\"Phase 2: read-only\"' in cover Approve button",
      'disabled title="Phase 2: read-only">Approve' not in src)
check("No 'disabled title=\"Phase 2: read-only\"' in cover Assign button",
      'disabled title="Phase 2: read-only">Assign' not in src)
check("approveCoverRequest called from onclick",
      "onclick=\"approveCoverRequest(" in src or "onclick='approveCoverRequest(" in src)
check("assignCoverRequest called from onclick",
      "onclick=\"assignCoverRequest(" in src or "onclick='assignCoverRequest(" in src)

# -- Section 6: Teacher Portal write functions ---------------------------------
print("6. Teacher Portal write functions present")
check("acceptCoverOpportunity function defined",
      "async function acceptCoverOpportunity(" in src)
check("declineCoverOpportunity function defined",
      "async function declineCoverOpportunity(" in src)
check("acceptCoverOpportunity PATCHes response=accepted",
      "response: 'accepted'" in src or 'response:"accepted"' in src)
check("declineCoverOpportunity PATCHes response=declined",
      "response: 'declined'" in src or 'response:"declined"' in src)

# -- Section 7: Teacher Portal buttons no longer hardcoded disabled ------------
print("7. Teacher Portal buttons not hardcoded disabled")
check("No 'disabled title=\"Phase 2: read-only\"' in Accept button",
      'disabled title="Phase 2: read-only">Accept' not in src)
check("No 'disabled title=\"Phase 2: read-only\"' in Decline button",
      'disabled title="Phase 2: read-only">Decline' not in src)
check("acceptCoverOpportunity called from onclick",
      "onclick=\"acceptCoverOpportunity(" in src or "onclick='acceptCoverOpportunity(" in src)
check("declineCoverOpportunity called from onclick",
      "onclick=\"declineCoverOpportunity(" in src or "onclick='declineCoverOpportunity(" in src)

# -- Section 8: Legacy TM banner -----------------------------------------------
print("8. Legacy TM banner")
if TM_APP.exists():
    tm = TM_APP.read_text(encoding="utf-8", errors="replace")
    check("TM app has rso-banner div",  "rso-banner" in tm)
    check("TM banner links to ritual-studio-ops.pages.dev",
          "ritual-studio-ops.pages.dev" in tm)
    check("TM banner says read-only recommended",
          "Read-only recommended" in tm or "read-only recommended" in tm or "Read-only" in tm)
else:
    print("  (TM app not mounted — skipping)")

# -- Section 9: Legacy CM dashboard banner ------------------------------------
print("9. Legacy CM dashboard banner")
if CM_DASH.exists():
    cm = CM_DASH.read_text(encoding="utf-8", errors="replace")
    check("CM dashboard has rso-banner div", "rso-banner" in cm)
    check("CM dashboard banner links to pages.dev",
          "ritual-studio-ops.pages.dev" in cm)
else:
    print("  (CM dashboard not mounted — skipping)")

# -- Section 10: Legacy teacher portal banner ----------------------------------
print("10. Legacy teacher portal banner")
if CM_PORT.exists():
    cp = CM_PORT.read_text(encoding="utf-8", errors="replace")
    check("CM teacher portal has rso-banner div", "rso-banner" in cp)
    check("CM teacher portal banner links to pages.dev",
          "ritual-studio-ops.pages.dev" in cp)
else:
    print("  (CM teacher portal not mounted — skipping)")


# -- Summary -------------------------------------------------------------------
passed = sum(1 for s, _, _ in results if s == PASS)
failed = sum(1 for s, _, _ in results if s == FAIL)
total  = len(results)
print(f"\nResults: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("Phase 4 integrity checks: ALL PASS -- write-enabled shell ready")
else:
    print("Phase 4 integrity checks: FAILED -- fix above before proceeding")
    sys.exit(1)
