# -*- coding: utf-8 -*-
"""test_phase3.py -- Phase 3 integrity tests for Ritual Studio Ops.

Tests:
  1. services/cover/ directory structure (all stage directories present)
  2. Key Python files copied correctly
  3. config.py conventions (RSO-rooted .env lookup, momence path setup)
  4. MomenceAPIClient import hacks removed from stage copies
  5. --insert-new flag present in momence_teacher_sync.py
  6. .env.template completeness (Phase 3 variables present)
  7. Original CM pipeline untouched (parallel-run safety)
"""
import sys
from pathlib import Path

ROOT   = Path(__file__).parent.parent
COVER  = ROOT / "services" / "cover"
CM_DIR = Path(r"C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management")

PASS = "OK"; FAIL = "FAIL"; results = []

def check(description, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, description, detail))
    if not condition:
        msg = f"  {FAIL}: {description}"
        if detail: msg += f" -- {detail}"
        print(msg)
    return condition


# ── Section 1: Directory structure ────────────────────────────────────────────
print("1. services/cover/ directory structure")
check("services/cover/ exists", COVER.is_dir())
for stage in ["stage1", "stage2", "stage3", "stage4", "stage6", "stage7", "tools"]:
    check(f"services/cover/{stage}/ present", (COVER / stage).is_dir())


# ── Section 2: Key files copied ───────────────────────────────────────────────
print("2. Key files copied")
expected_files = [
    "config.py",
    "stage1/momence_teacher_sync.py",
    "stage2/cover_processor.py",
    "stage2/nlp_parser.py",
    "stage2/whatsapp_monitor.py",
    "stage3/momence_crosscheck.py",
    "stage3/enrich_resolved_classes_from_momence.py",
    "stage4/cover_workflow.py",
    "stage4/notifier.py",
    "stage4/teacher_matcher.py",
    "stage6/cancellation_workflow.py",
    "stage6/momence_updater.py",
    "stage7/link_generator.py",
]
for rel in expected_files:
    p = COVER / rel
    check(f"{rel} exists", p.exists())
    if p.exists():
        check(f"{rel} non-empty", p.stat().st_size > 100, f"{p.stat().st_size} bytes")


# ── Section 3: config.py conventions ─────────────────────────────────────────
print("3. services/cover/config.py RSO conventions")
cfg_path = COVER / "config.py"
if cfg_path.exists():
    cfg = cfg_path.read_text(encoding="utf-8")
    check("config.py resolves .env from RSO root (parent.parent)",
          "_RSO_ROOT = _HERE.parent.parent" in cfg or
          "parent.parent" in cfg)
    check("config.py adds services/momence/ to sys.path",
          "_MOMENCE_SERVICES" in cfg and 'sys.path.insert' in cfg)
    check("config.py: SUPABASE_URL defined", "SUPABASE_URL" in cfg)
    check("config.py: ANTHROPIC_API_KEY defined", "ANTHROPIC_API_KEY" in cfg)
    check("config.py: DISCIPLINE_CODES defined", "DISCIPLINE_CODES" in cfg)
    check("config.py: sb_get/sb_post/sb_patch helpers defined",
          "def sb_get" in cfg and "def sb_post" in cfg and "def sb_patch" in cfg)
    check("config.py: SMTP settings defined", "SMTP_HOST" in cfg)
    check("config.py: MOMENCE_DATA_DIR defined", "MOMENCE_DATA_DIR" in cfg)
    check("config.py: no _MOMENCE_DIR variable assignment (OneDrive path must be env-var backed)",
          "_MOMENCE_DIR =" not in cfg and "_MOMENCE_DIR=" not in cfg)


# ── Section 4: Momence import hacks removed ───────────────────────────────────
print("4. Hardcoded Momence path hacks removed from stage copies")
files_patched = [
    "stage1/momence_teacher_sync.py",
    "stage3/enrich_resolved_classes_from_momence.py",
    "stage6/cancellation_workflow.py",
    "stage6/momence_updater.py",
]
HACK_MARKER = r"C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data"
for rel in files_patched:
    p = COVER / rel
    if p.exists():
        content = p.read_text(encoding="utf-8")
        check(f"{rel}: hardcoded Momence path removed",
              HACK_MARKER not in content,
              "still contains hardcoded OneDrive path")


# ── Section 5: --insert-new flag ──────────────────────────────────────────────
print("5. --insert-new flag in momence_teacher_sync.py")
sync_path = COVER / "stage1" / "momence_teacher_sync.py"
if sync_path.exists():
    sync = sync_path.read_text(encoding="utf-8")
    check("--insert-new argument defined", '"--insert-new"' in sync)
    check("insert_new parameter in run()", "insert_new" in sync)
    check("INSERT logic present (sb_post call)",
          "sb_post" in sync and "INSERT" in sync.upper())
    check("--insert-new in docstring or usage", "insert-new" in sync or "insert_new" in sync)
    check("run() signature accepts insert_new",
          "def run(" in sync and "insert_new" in sync)


# ── Section 6: .env.template completeness ────────────────────────────────────
print("6. .env.template Phase 3 variables")
tmpl = (ROOT / ".env.template").read_text(encoding="utf-8")
for var in [
    "ANTHROPIC_API_KEY", "NLP_MODEL",
    "GEMINI_API_KEY", "GEMINI_MODEL",
    "INITIAL_TEACHER_GRADE", "SYNC_LOOKBACK_DAYS",
    "WHATSAPP_LOOKBACK_HOURS", "NLP_CONFIDENCE_THRESHOLD",
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "CHROME_DEBUG_PORT",
]:
    check(f".env.template: {var} present", var in tmpl)


# ── Section 7: Original CM pipeline untouched ─────────────────────────────────
print("7. Original CM pipeline untouched (parallel-run safety)")
if CM_DIR.exists():
    cm_sync = CM_DIR / "stage1" / "momence_teacher_sync.py"
    if cm_sync.exists():
        cm_src = cm_sync.read_text(encoding="utf-8")
        check("CM stage1 still has original _MOMENCE_DIR hack (untouched)",
              "_MOMENCE_DIR" in cm_src,
              "Original file appears to have been modified — check immediately")
    cm_cfg = CM_DIR / "config.py"
    if cm_cfg.exists():
        cm_cfg_src = cm_cfg.read_text(encoding="utf-8")
        check("CM config.py still looks up .env from CM root (untouched)",
              "_HERE.parent / \".env\"" in cm_cfg_src or
              '_env_path = _HERE / ".env"' in cm_cfg_src)
else:
    print("  (CM directory not mounted — skipping parallel-run safety checks)")


# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(1 for s, _, _ in results if s == PASS)
failed = sum(1 for s, _, _ in results if s == FAIL)
total  = len(results)
print(f"\nResults: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("Phase 3 integrity checks: ALL PASS -- pipeline re-pointed")
else:
    print("Phase 3 integrity checks: FAILED -- fix above before proceeding")
    sys.exit(1)
