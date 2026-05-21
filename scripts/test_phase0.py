# -*- coding: utf-8 -*-
"""
test_phase0.py -- Phase 0 skeleton integrity tests
Run from the Ritual_Studio_Ops root:
    python scripts/test_phase0.py

All tests must pass before Phase 1 begins.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PASS = "OK"
FAIL = "FAIL"
results = []


def check(description, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, description, detail))
    if not condition:
        msg = f"  {FAIL}: {description}"
        if detail:
            msg += f" -- {detail}"
        print(msg)
    return condition


# -- 1. Directory structure ---------------------------------------------------
print("\n[1] Directory structure")
required_dirs = [
    "app",
    "services/momence",
    "services/momence/scraper",
    "services/momence/sync",
    "services/momence/docs",
    "services/cover",
    "migrations",
    "scripts",
    "docs",
]
for d in required_dirs:
    check(f"Directory exists: {d}", (ROOT / d).is_dir())


# -- 2. Required core files ---------------------------------------------------
print("\n[2] Required core files")
required_files = [
    ".env.template",
    ".gitignore",
    "wrangler.toml",
    "docs/README.md",
    "docs/DOCS_INDEX.md",
    "docs/CHANGELOG.md",
    "docs/LESSONS_LEARNED.md",
    "docs/Ritual_Studio_Ops_Merger_Plan_v2.md",
    "app/README.md",
    "app/ritual-teacher-management31.html",
    "app/cover_dashboard_ref.html",
    "app/teacher_portal_ref.html",
    "services/momence/README.md",
    "services/cover/README.md",
    "scripts/test_phase0.py",
]
for f in required_files:
    check(f"File exists: {f}", (ROOT / f).is_file())


# -- 3. .env.template keys ----------------------------------------------------
print("\n[3] .env.template")
env_template = ROOT / ".env.template"
if env_template.exists():
    et = env_template.read_text(encoding="utf-8")
    for key in ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY",
                "MOMENCE_CLIENT_ID", "MOMENCE_CLIENT_SECRET",
                "MOMENCE_DATA_DIR", "WRITES_ENABLED"]:
        check(f".env.template has key: {key}", key in et)
    check("MOMENCE_DATA_DIR references MFPL OneDrive", "OneDrive - MFPL" in et)
    check("WRITES_ENABLED defaults to false", "WRITES_ENABLED=false" in et)
check(".env absent (secrets not committed)", not (ROOT / ".env").exists())


# -- 4. .gitignore ------------------------------------------------------------
print("\n[4] .gitignore")
gi = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
for pattern in [".env", "__pycache__/", "*.log", "node_modules/"]:
    check(f".gitignore includes: {pattern}", pattern in gi)


# -- 5. Governance documents --------------------------------------------------
print("\n[5] Governance document content")
di = (ROOT / "docs/DOCS_INDEX.md").read_text(encoding="utf-8")
check("DOCS_INDEX references Teacher Management", "Teacher Management" in di)
check("DOCS_INDEX references Cover Management", "Cover Management" in di)
check("DOCS_INDEX references Momence_data", "Momence_data" in di)
check("DOCS_INDEX references Ritual Dashboard", "Ritual Dashboard" in di)
check("DOCS_INDEX has tables-and-owners matrix", "momence_sessions" in di)
check("DOCS_INDEX lists v31 as canonical", "v31" in di and "Canonical" in di)
check("DOCS_INDEX notes Mermaid as closed", "Mermaid" in di and "is_active = false" in di)
check("DOCS_INDEX canonical Momence docs in services/momence/docs", "services/momence/docs" in di)
check("DOCS_INDEX marks Dashboard scraping docs as superseded",
      "superseded" in di and "Dashboard" in di)

cl = (ROOT / "docs/CHANGELOG.md").read_text(encoding="utf-8")
check("CHANGELOG has Phase 0 entry", "Phase 0" in cl)
check("CHANGELOG has TM entries", "TM" in cl or "Teacher Management" in cl)
check("CHANGELOG has CM entries", "CM" in cl or "Cover Management" in cl)

ll = (ROOT / "docs/LESSONS_LEARNED.md").read_text(encoding="utf-8")
check("LESSONS_LEARNED has navigator.locks lesson", "navigator.locks" in ll)
check("LESSONS_LEARNED has sbClient lesson", "sbClient" in ll)
check("LESSONS_LEARNED has RLS recursion lesson", "RLS" in ll and "recursion" in ll)
check("LESSONS_LEARNED has Verify JWT lesson", "Verify JWT" in ll)
check("LESSONS_LEARNED has anon PII risk", "anon_read_teacher_names" in ll)
check("LESSONS_LEARNED has Mermaid decision", "Mermaid" in ll and "closed" in ll.lower())
check("LESSONS_LEARNED has Momence rate limit", "rate limit" in ll.lower())


# -- 6. v31 TM app ------------------------------------------------------------
print("\n[6] v31 TM app integrity")
v31 = ROOT / "app/ritual-teacher-management31.html"
if v31.exists():
    v31c = v31.read_text(encoding="utf-8", errors="replace")
    check("v31 is non-empty (> 100KB)", len(v31c) > 100_000,
          f"Actual: {len(v31c):,} bytes")
    check("v31 uses sbClient", "sbClient" in v31c)
    check("v31 uses onAuthStateChange", "onAuthStateChange" in v31c)
    check("v31 does not use sbClient.from() (should use direct REST)",
          "sbClient.from(" not in v31c)
else:
    check("v31 file exists", False)


# -- 7. Git repository --------------------------------------------------------
print("\n[7] Git repository")
check("Git repository initialised", (ROOT / ".git").is_dir())
check("HEAD file present", (ROOT / ".git/HEAD").is_file())


# -- 8. Momence core code files -----------------------------------------------
print("\n[8] Momence code files")
momence_root = ROOT / "services/momence"

for f in ["momence_api_client.py", "momence_data_service.py",
          "momence_service_client.py", "config.py",
          "Run_Momence_Chain.bat", "write_batch_log.ps1"]:
    check(f"services/momence/{f}", (momence_root / f).is_file())

cfg = (momence_root / "config.py").read_text(encoding="utf-8") if (momence_root / "config.py").exists() else ""
check("config.py uses MOMENCE_DATA_DIR env var", "MOMENCE_DATA_DIR" in cfg)
check("config.py has _DATA_DIR", "_DATA_DIR" in cfg)
check("config.py falls back when env var absent", "_CODE_DIR" in cfg)
check("config.py documents original chain unaffected", "unaffected" in cfg.lower() or "original" in cfg.lower())


# -- 9. Momence scraper scripts -----------------------------------------------
print("\n[9] Momence scraper scripts in services/momence/scraper/")
scraper_scripts = [
    "check_cookie_expiry.py",
    "momence_sessions_api.py",
    "momence_sessions_scrape_lite.py",
    "extract_full_classes2.py",
    "momence_class_customers_full_api.py",
    "momence_waitlist_scrape.py",
    "Momence_bookings_update.py",
    "Momence_no_card_customers.py",
    "extract_all_classes_1.py",
    "momence_class_customers_api.py",
    "momence_courses_sync.py",
    "momence_new_reports.py",
    "build_master_customers.py",
    "archive_old_files.py",
    "chain_heartbeat_guard.py",
]
for f in scraper_scripts:
    check(f"scraper/{f}", (momence_root / "scraper" / f).is_file())

check("services/momence/sync/ exists (Phase 7 placeholder)",
      (momence_root / "sync").is_dir())


# -- 10. Momence documentation ------------------------------------------------
print("\n[10] Momence documentation in services/momence/docs/")
momence_docs = [
    "Momence_data_scraping_wisdom.md",
    "TECHNICAL_DETAILS.md",
    "Momence_API_v2_Reference.md",
    "Momence_Cookie_Auth_Reference.md",
    "PIPELINE_MAINTENANCE_GUIDE.md",
    "HANDOVER_NOTES.md",
    "INSTALLATION_SETUP_GUIDE.md",
]
for f in momence_docs:
    check(f"docs/{f}", (momence_root / "docs" / f).is_file())


# -- 11. Cloudflare / wrangler.toml ------------------------------------------
print("\n[11] Cloudflare configuration")
wt = (ROOT / "wrangler.toml").read_text(encoding="utf-8") if (ROOT / "wrangler.toml").exists() else ""
check("wrangler.toml has project name", "ritual-studio-ops" in wt)
check("wrangler.toml has pages_build_output_dir = app", 'pages_build_output_dir = "app"' in wt)
check("wrangler.toml has production env block", "[env.production]" in wt)


# -- Summary ------------------------------------------------------------------
print("\n" + "=" * 60)
passed = sum(1 for s, _, _ in results if s == PASS)
failed = sum(1 for s, _, _ in results if s == FAIL)
total = len(results)
print(f"Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("Phase 0 integrity checks: ALL PASS -- ready for Phase 1")
else:
    print("Phase 0 integrity checks: FAILED -- fix above before Phase 1")
    sys.exit(1)
n(results)
print(f"Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("Phase 0 integrity checks: ALL PASS -- ready for Phase 1")
else:
    print("Phase 0 integrity checks: FAILED -- fix above before Phase 1")
    sys.exit(1)
