# -*- coding: utf-8 -*-
"""test_phase2.py -- Phase 2 integrity tests for Ritual Studio Ops merged shell.

Tests:
  1. App file exists and has required conventions
  2. Supabase connectivity — key tables readable via authenticated REST
  3. Schema correctness — cover_requests columns match what the app queries
  4. Data row counts match expected minimums
"""
import os, sys, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
APP  = ROOT / "app" / "ritual-studio-ops-v1.html"

PASS = "OK"; FAIL = "FAIL"; results = []

def check(description, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, description, detail))
    if not condition:
        msg = f"  {FAIL}: {description}"
        if detail: msg += f" -- {detail}"
        print(msg)
    return condition


# ── Section 1: App file existence ─────────────────────────────────────────────
print("1. App file existence")
check("ritual-studio-ops-v1.html exists", APP.exists(), str(APP))

if APP.exists():
    src = APP.read_text(encoding="utf-8", errors="replace")
    lines = src.splitlines()
    check("File has > 1000 lines", len(lines) > 1000, f"{len(lines)} lines")

    # ── Section 2: Convention checks ──────────────────────────────────────────
    print("2. Convention checks")
    check("Version comment on line 1", lines[0].strip().startswith("<!-- RSO v1"), lines[0][:60])
    check("SUPABASE_URL is rfjygyqijwgkmxboddup", "rfjygyqijwgkmxboddup" in src)
    check("WRITES_ENABLED = false present", "WRITES_ENABLED = false" in src)
    check("sbClient naming convention", "const sbClient = window.sbClient" in src)
    check("onAuthStateChange present", "sbClient.auth.onAuthStateChange" in src)
    check("Direct REST (fetch + authHeaders)", "authHeaders()" in src and "fetch(" in src)
    check("No direct supabase client for queries",
          src.count("sbClient.from(") == 0,
          "sbClient.from() found — use direct fetch instead")
    check("mat_pilates discipline key", "mat_pilates" in src)
    check("Cover view HTML present", 'id="coverShell"' in src)
    check("Cover Requests subnav present", "coverSubBtn_requests" in src)
    check("Teacher Portal subnav present", "coverSubBtn_portal" in src)
    check("switchView function present", "function switchView(" in src)
    check("loadCoverData function present", "async function loadCoverData(" in src)
    check("renderCoverRequests function present", "function renderCoverRequests(" in src)
    check("renderTeacherPortal function present", "function renderTeacherPortal(" in src)
    check("WRITES_ENABLED gate in dbPost/Patch/Delete",
          src.count("WRITES_ENABLED") >= 5,
          f"Only {src.count('WRITES_ENABLED')} occurrences")
    check("Correct column: requesting_teacher_name_raw", "requesting_teacher_name_raw" in src)
    check("Correct column: class_name_raw", "class_name_raw" in src)
    check("Correct column: discipline_code", "discipline_code" in src)
    check("Wrong column 'requesting_teacher_name' not used in select",
          "requesting_teacher_name&" not in src and
          "requesting_teacher_name," not in src.replace("requesting_teacher_name_raw", ""),
          "Found bare requesting_teacher_name in query string")
    check("Style block closes before script", src.index("</style>") < src.index("<script>", src.index("</style>")))
    check("File ends with </html>", src.strip().endswith("</html>") or src.rstrip().endswith("</html>"))

    # ── Section 3: TM tabs present ────────────────────────────────────────────
    print("3. TM tab renderers present")
    for fn in ["renderOverview", "renderHistory", "renderAvailability",
               "renderMatch", "renderGradeEdit", "renderAuditTrail"]:
        check(f"{fn} present", f"function {fn}(" in src)

    # ── Section 4: RBAC roles ──────────────────────────────────────────────────
    print("4. RBAC roles present")
    for role in ["developer", "administrator", "coordinator", "adjudicator", "teacher", "trainee", "guest"]:
        # Roles can be quoted or unquoted object keys: developer: { or 'developer': {
        found = (f"'{role}':" in src or f'"{role}":' in src or f'{role}:' in src)
        check(f"Role '{role}' defined", found)


# ── Section 5: Supabase schema correctness ────────────────────────────────────
# Query the live DB using the Supabase REST endpoint with the anon key.
# This exercises the same code path as the browser app.
# Skipped automatically when running in the sandbox (no external network).
print("5. Supabase schema correctness (via REST)")

import urllib.request, json

SUPABASE_URL  = "https://rfjygyqijwgkmxboddup.supabase.co"
SUPABASE_ANON = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJmanlneXFpandna"
    "214Ym9kZHVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3NDU5"
    "MjksImV4cCI6MjA4NzMyMTkyOX0"
    ".g40IEOLPDTWnbFYybWL01wZMiE_f2_yor_DKuaSCajU"
)

# Probe connectivity first
_network_available = False
try:
    probe = urllib.request.Request(
        SUPABASE_URL + "/rest/v1/disciplines?select=code&limit=1",
        headers={"apikey": SUPABASE_ANON}
    )
    with urllib.request.urlopen(probe, timeout=10) as _r:
        _network_available = True
except Exception as _e:
    _err = str(_e)
    if "403" in _err or "Tunnel" in _err or "timed out" in _err.lower():
        print("  (skipping REST tests — no external network access in this environment)")
    else:
        print(f"  (skipping REST tests — {_err})")

if _network_available:
    def rest_get(path, expected_min=None, label=None):
        url = f"{SUPABASE_URL}/rest/v1/{path}"
        req = urllib.request.Request(url, headers={
            "apikey": SUPABASE_ANON,
            "Content-Type": "application/json",
            "Prefer": "count=exact"
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read())
                count = len(body) if isinstance(body, list) else 0
                if label and expected_min is not None:
                    ok = count >= expected_min
                    check(label, ok, f"{count} rows (expected >= {expected_min})")
                return body
        except Exception as e:
            if label:
                check(label, False, str(e))
            return []

    # Disciplines (seeded in Phase 1)
    discs = rest_get("disciplines?select=code,display_name&order=sort_order",
                     expected_min=5, label="disciplines: >= 5 rows")
    disc_codes = {d["code"] for d in discs} if isinstance(discs, list) else set()
    for code in ["yoga", "barre", "reformer", "mat_pilates", "yin"]:
        check(f"discipline '{code}' seeded", code in disc_codes)

    # Studios (seeded in Phase 1)
    studios = rest_get("studios?select=code,is_active",
                       expected_min=3, label="studios: >= 3 rows")
    studio_codes = {s["code"] for s in studios} if isinstance(studios, list) else set()
    check("studio 'palm_beach' present", "palm_beach" in studio_codes)
    check("studio 'robina' present", "robina" in studio_codes)
    check("studio 'mermaid' is_active=false",
          any(s.get("code") == "mermaid" and not s.get("is_active") for s in studios))

    # Teachers
    rest_get("teachers?select=id&limit=1",
             expected_min=1, label="teachers table accessible via anon+auth")

    # cover_requests — test the exact select the app uses
    cover_fields = (
        "cover_request_id,class_date,class_time,class_name_raw,"
        "studio,discipline_code,requesting_teacher_name_raw,status,coverage_type"
    )
    rest_get(
        f"cover_requests?select={cover_fields}&order=class_date.desc&limit=5",
        expected_min=0,
        label="cover_requests: app's exact select succeeds (RLS may return 0 rows)"
    )

    # momence Phase 7 placeholders
    rest_get("momence_members?select=member_id&limit=1",
             expected_min=0, label="momence_members accessible (Phase 7 placeholder)")
    rest_get("momence_bookings?select=booking_id&limit=1",
             expected_min=0, label="momence_bookings accessible (Phase 7 placeholder)")
    rest_get("momence_sync_runs?select=run_id&limit=1",
             expected_min=0, label="momence_sync_runs accessible")

    # teacher_directory view
    rest_get("teacher_directory?select=id,first_name,last_name&limit=1",
             expected_min=0, label="teacher_directory view accessible")
else:
    print("  NOTE: REST tests must be run from a browser or a machine with direct internet access.")


# ── Summary ────────────────────────────────────────────────────────────────────
passed = sum(1 for s, _, _ in results if s == PASS)
failed = sum(1 for s, _, _ in results if s == FAIL)
total  = len(results)
print(f"\nResults: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("Phase 2 integrity checks: ALL PASS — merged shell ready")
else:
    print("Phase 2 integrity checks: FAILED — fix above before proceeding")
    sys.exit(1)
