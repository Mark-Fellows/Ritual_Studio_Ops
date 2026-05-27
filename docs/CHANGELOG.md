# Ritual Studio Ops — Master Changelog

All significant changes to schema, code, configuration, and documentation across all four Ritual technology projects, in reverse chronological order.

Individual project changelogs are NOT the authoritative record from Phase 0 onwards — this file is. Add a one-line entry here first, then write detail in the project-level file if needed.

Format: `YYYY-MM-DD | Project | Summary | Files changed`

---

## 2026-05-27 | Ritual Studio Ops | Portal & access fixes — Cover Dashboard deep-link, magic-link auth redirect, footer badge standard

**Cover Dashboard deep-link (`index.html` + `ritual-studio-ops-v2.html`):**
The Cover Dashboard portal tile was pointing to `./ritual-studio-ops-v2.html` with no hash, so the merged app always opened on the Teachers view. Per `NAVIGATION.md`, both portal tiles correctly resolve to the merged app — the fix was to add `#cover` to the Cover Dashboard tile href and add a three-line hash check in `onSignedIn`: `if (window.location.hash === '#cover') switchView('cover');`. Teacher Portal tile unchanged at `./ritual-studio-ops-v2.html`.

An earlier incorrect intermediate fix had linked the tile to `https://ritual-cover-management.pages.dev/cover_dashboard.html` (the legacy read-only site). That link was reverted.

**Magic-link `emailRedirectTo` (`index.html`):**
`emailRedirectTo` was `window.location.origin + window.location.pathname`. When the Supabase Site URL was still set to `ritual-cover-management.pages.dev` (not yet updated after the merger), Supabase ignored the dynamic value and sent magic-link emails to the wrong domain. Fixed to hardcoded `'https://ritual-studio-ops.pages.dev'`. Supabase Auth → URL Configuration → Site URL and Allowed Redirect URLs must also be updated to `https://ritual-studio-ops.pages.dev`.

**Footer badge standard (all 7 portal pages):**
All `data-file-id="rso-file-footer"` divs across all apps had `pointer-events:none`, making the filename unselectable and uncopable. Replaced with `cursor:pointer; user-select:text;` and added an `onclick` click-to-copy handler (copies path to clipboard, briefly shows "Copied!"). `cover_dashboard.html` footer now includes the version string `v1.3.22`.

Files: `Ritual_Studio_Ops/app/index.html`, `Ritual_Studio_Ops/app/ritual-studio-ops-v2.html`, `Ritual_Cover_Management/public/cover_dashboard.html`, `Ritual_Cover_Management/public/index.html`, `Ritual_Cover_Management/public/studio_timetable.html`, `Ritual_Cover_Management/public/teacher_portal.html`, `Ritual marketing/campaign-planning.html`

---

## 2026-05-27 | Teacher Management | Teacher absence tracking implemented — per-teacher panel, global Absences view, on-leave sidebar pill, availability banner, soft-delete archive, five RLS policies; migration applied via Supabase MCP

Files: `Ritual_Teacher_Management/ritual-teacher-management31.html`, `Ritual_Teacher_Management/migrations/2026-05-26-teacher-absences.sql`, `Ritual_Teacher_Management/Ritual Teacher Management/Teacher_Absences_Design.md`

---

## 2026-05-22 | Ritual Studio Ops | Manual cover request entry — v2 app, Edge Function, schema

New feature: administrators and coordinators can now manually create a cover request from the Cover Requests tab without it going through the WhatsApp pipeline. Handles privately messaged requests.

**Schema (applied via Supabase MCP):** `cover_requests.source TEXT DEFAULT 'whatsapp'` added. Manual entries carry `source = 'manual'`; existing WhatsApp pipeline records keep the default.

**Edge Function:** `parse-cover-request` deployed to Supabase (project rfjygyqijwgkmxboddup). Accepts raw message text plus teacher/discipline/studio context. Calls Claude Haiku via Anthropic API. Returns structured fields (teacher name, date, time, class name, studio, discipline, coverage type) and a list of clarifying questions for anything ambiguous or missing. JWT-verified; uses ANTHROPIC_API_KEY from Supabase secrets.

**App v2 (`ritual-studio-ops-v2.html`):**
- Version comment and build stamp updated from v1/Phase 4 to v2/Phase 5.
- "New Manual Request" button added to Cover Requests tab header (visible to developer, administrator, coordinator roles only).
- Two-step modal: Step 1 — instruction reminder + free-text area + "Parse with AI" button. Step 2 — pre-filled editable fields (teacher, date, time, class name, studio dropdown, discipline dropdown, coverage type dropdown) plus inline clarifying question inputs from the AI response. Submit writes to `cover_requests` with `status = pending`, `source = manual`, and an `admin_notes` field recording the creating user. `writeAudit` called with `[RSO]` prefix.
- Escape key handler updated to close the new modal.
- `detectSessionInUrl` corrected from `false` to `true` (magic link login fix).

**Deploy bat:** `rso_deploy.bat` updated to copy v2 not v1 to the staging folder.

Files: `app/ritual-studio-ops-v2.html`, `migrations/2026-05-22-add-source-to-cover-requests.sql`, `docs/CHANGELOG.md`
(Edge Function deployed directly via Supabase MCP — no local file.)

---

---

## 2026-05-22 | Ritual Studio Ops | Docs update — all governance documents brought to Phase 5

DOCS_INDEX.md: updated `Last updated` to Phase 5, fixed Merger Plan v2 location (was still pointing to TM folder), corrected TM v31 status to `Legacy` (RSO Phase 4 banner added), added all Phase 2-5 RSO deliverables to section 7 (app/ritual-studio-ops-v1.html, test_phase2-5.py, reconcile.py, reconcile_reports/).

README.md: phase status table updated (Phases 0-4 Complete, Phase 5 In progress), RSO target URL updated from `*(to be created)*` to active Pages URL, directory structure updated from ritual-teacher-management31.html to ritual-studio-ops-v1.html, Merger Plan v2 location reference corrected, key contacts table updated.

LESSONS_LEARNED.md: five new lessons added (L-MG-04 through L-MG-08) covering Write tool truncation on OneDrive mounts, UTF-8 box-drawing character truncation, test string matching against variable assignments not substrings, Desktop Commander `cd /d` failure with space-containing paths, and phase-specific .bat file discipline for git commits.

Files: `docs/DOCS_INDEX.md`, `docs/README.md`, `docs/LESSONS_LEARNED.md`, `docs/CHANGELOG.md`

---

## 2026-05-22 | Ritual Studio Ops | Phase 5: Reconciliation script

New file: `scripts/reconcile.py` — daily parallel-run health check. Run once per day during the two-week Phase 5 soak period.

Checks performed on each run: (1) Audit log origin split — counts `[RSO]`-prefixed vs non-prefixed entries in the last 24h; any non-RSO entries trigger a P1 flag indicating a legacy app is still making writes. (2) Cover requests by status — reports current distribution and flags if total count drops (unexpected deletion). (3) Trainee bookings by status — flags unusual growth in pending count. (4) Teacher record count — flags any unexpected drop.

Snapshot mechanism: current state saved to `scripts/reconcile_state.json` after each run; compared against yesterday's snapshot on the next run to detect drift between runs.

Report output: plain-text report written to `scripts/reconcile_reports/YYYY-MM-DD.txt` and stdout. Exit code 0 = green, exit code 1 = P1 issue detected.

Usage: `python scripts/reconcile.py [--days N] [--no-save]`

Graceful degradation: all Supabase queries wrapped in `safe_get()`; network failures produce WARN not P1 (so the script never crashes the scheduled task).

Test suite: `scripts/test_phase5.py` — 28 checks.

Operational note: "two green weeks" and "Dashboard parity confirmation" are manual sign-off steps performed by the studio team, not automated. Run `reconcile.py --no-save` at any time for a spot-check without disturbing the snapshot.

Files: `scripts/reconcile.py`, `scripts/test_phase5.py`, `scripts/reconcile_reports/.gitkeep`

---

## 2026-05-22 | Ritual Studio Ops | Phase 4: Write-enabled shell

`WRITES_ENABLED` flipped to `true`. All TM write operations were already wired; Cover and Portal writes added.

New write operations: `approveCoverRequest(requestId)` — PATCHes `cover_requests` status to `approved`, sets `reviewed_by` / `reviewed_at`. `assignCoverRequest(requestId, className)` — prompts for notes, PATCHes status to `covered`. `acceptCoverOpportunity(candidateId, requestId)` — PATCHes `cover_candidates` response to `accepted`. `declineCoverOpportunity(candidateId, requestId)` — confirms, PATCHes to `declined`. All call `writeAudit`.

Audit origin: `writeAudit` now prefixes every description with `[RSO]` so writes from this app are distinguishable from legacy-app writes in `audit_log`.

Legacy banners added to `ritual-teacher-management31.html`, `public/cover_dashboard.html`, and `public/teacher_portal.html` — fixed bar linking to `ritual-studio-ops.pages.dev`, text: "Read-only recommended — use Ritual Studio Ops for all edits."

Version comment, build stamp, and Settings section updated to Phase 4.

Test suite: `scripts/test_phase4.py` — 24 checks (sandbox) covering WRITES_ENABLED, [RSO] prefix, write functions, onclick wiring, no hardcoded disabled buttons, legacy banners.

Files: `app/ritual-studio-ops-v1.html`, `scripts/test_phase4.py`, `Ritual_Teacher_Management/ritual-teacher-management31.html`, `Ritual_Cover_Management/public/cover_dashboard.html`, `Ritual_Cover_Management/public/teacher_portal.html`

---

## 2026-05-22 | Ritual Studio Ops | Phase 3: Cover pipeline re-pointed to RSO

All CM stage scripts (stages 1–7) copied to `services/cover/`. Original CM pipeline untouched — parallel-run safe.

New file: `services/cover/config.py` — RSO edition. Resolves `.env` from `Ritual_Studio_Ops/` root (`_RSO_ROOT = _HERE.parent.parent`). Adds `services/momence/` to `sys.path` so `MomenceAPIClient` imports without hardcoded OneDrive paths. Identical public API to CM `config.py` plus `DISCIPLINE_CODES` (canonical Phase 1 codes), `MOMENCE_DATA_DIR` (env-var backed), and `WRITES_ENABLED` default.

Hardcoded `_MOMENCE_DIR` OneDrive path hacks removed from: `stage1/momence_teacher_sync.py`, `stage3/enrich_resolved_classes_from_momence.py`, `stage6/cancellation_workflow.py`, `stage6/momence_updater.py`. Each now imports from `config`.

New feature: `--insert-new` flag in `stage1/momence_teacher_sync.py`. When set, unmatched Momence teachers are inserted to Supabase via `sb_post` rather than being silently skipped. Inserted rows carry `INITIAL_TEACHER_GRADE` and auto-generated `notes`.

`.env.template` extended with Phase 3 variables: `ANTHROPIC_API_KEY`, `NLP_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `INITIAL_TEACHER_GRADE`, `SYNC_LOOKBACK_DAYS`, `WHATSAPP_LOOKBACK_HOURS`, `NLP_CONFIDENCE_THRESHOLD`, `SMTP_*`, `CHROME_DEBUG_PORT`, `CHROME_PATH`.

Test suite: `scripts/test_phase3.py` — 65 checks covering directory structure, file existence, config.py conventions, import-hack removal, `--insert-new` flag, `.env.template` completeness, parallel-run safety.

Files: `services/cover/` (all stage files + `config.py`), `.env.template`, `scripts/test_phase3.py`

---

## 2026-05-22 | Ritual Studio Ops | Cloudflare Pages project created

`ritual-studio-ops` Pages project created via `npx wrangler pages project create ritual-studio-ops`. Production branch: `master`. Staging URL reserved: `https://ritual-studio-ops.pages.dev/`. No deployment yet — first deploy deferred to Phase 4. Wrangler version 4.82.2 used (4.93.1 available).

---

## 2026-05-22 | Ritual Studio Ops | Phase 2: Read-only merged shell

New file: `app/ritual-studio-ops-v1.html` — single-file HTML/JS merged shell.

Conventions: `sbClient`/`window.sbClient`, `onAuthStateChange`, direct REST + cached JWT, `WRITES_ENABLED = false`.

Teachers view: all six TM tabs lifted verbatim (Overview, Class History, Availability, Allocation Check, Grades ✎, Audit Trail). Five-role RBAC preserved. All TM modals and trainee flows included.

Cover view (new): Cover Requests table (reads `cover_requests` with correct column names: `class_name_raw`, `discipline_code`, `requesting_teacher_name_raw`, `coverage_type`). Teacher Portal panel (reads `cover_candidates` filtered to signed-in teacher's profile). All action buttons disabled with Phase 2 tooltip.

Schema fix: corrected cover_requests column references after live schema audit — `requesting_teacher_name_raw` not `requesting_teacher_name`; `class_name_raw` not `class_name`; `discipline_code` not `discipline`; no `cover_teacher_name` column exists.

Test suite: `scripts/test_phase2.py` — 37 checks covering conventions, tab renderers, RBAC roles, REST schema (skipped in sandboxed environments).

Files: `app/ritual-studio-ops-v1.html`, `scripts/test_phase2.py`

---

## 2026-05-21 | Ritual Studio Ops | Phase 1: Schema reconciliation

Migration: `migrations/2026-05-merged-v1.sql` applied to Supabase (rfjygyqijwgkmxboddup).

New tables (all additive, RLS on, authenticated read):
- `disciplines` — 5 rows seeded: yoga, barre, reformer, mat_pilates, yin
- `studios` — 3 rows seeded: Palm Beach (active), Robina (active), Mermaid (is_active=false)
- `momence_members` — empty Phase 7 placeholder
- `momence_bookings` — empty Phase 7 placeholder
- `momence_sync_runs` — Phase 7 sync audit log

New view:
- `teacher_directory` — id, first_name, last_name (narrow identity view, gated by teachers RLS)

Schema discoveries:
- `momence_sessions` already exists with 7,365 rows (Phase 7 session sync already running via CM)
- `anon_read_teacher_names` policy does not exist — already resolved, no action needed
- 12 CM/TM tables have RLS disabled — flagged, not auto-fixed (requires policy design per table)
- 5 tables not previously in DOCS_INDEX added: `training_courses`, `trainee_enrollments`, `timeslots`, `permissions`, `role_permissions`

DOCS_INDEX updated: tables-and-owners matrix corrected and expanded to 24 tables.

Files: `migrations/2026-05-merged-v1.sql`, `docs/DOCS_INDEX.md`

---

## 2026-05-21 | Ritual Studio Ops | Phase 0: Project skeleton created

First commit of the merged project. Folder structure, .env template, .gitignore, governance documents (DOCS_INDEX, CHANGELOG, LESSONS_LEARNED), README, services/momence stub, services/cover stub.

Files: `Ritual_Studio_Ops/` (all Phase 0 files)
Note: Momence_data code copy PENDING — MFPL OneDrive not mounted. See `services/momence/README.md`.

---

## Pre-merger changelogs (absorbed from legacy projects)

The entries below summarise the legacy project changelogs. Original files are listed in DOCS_INDEX under their respective projects and remain in place.

---

### Cover Management

#### 2026-05-20 | CM | Dashboard spinning fix
Fix for dashboard spinner that did not stop after data load.
Source: `CHANGELOG-dashboard-spinning-fix-20260520.md`

#### 2026-05-17 | CM | RLS phase 1 permissions; WhatsApp message timestamp
Applied RLS policies to permissions tables. Added `received_at` timestamp column to `whatsapp_messages`.
Migrations: `MIGRATION-rls-phase1-permissions-tables-2026-05-17.sql`, `MIGRATION-whatsapp-message-timestamp-2026-05-17.sql`

#### 2026-05-16 | CM | Phase 4 offer matching planning
Design and planning changes for offer matching (Phase 4). No schema changes.
Source: `CHANGELOG-2026-05-16.md`, `PLAN-phase4-offer-matching-2026-05-16.md`

#### 2026-05-11 | CM | Momence sessions table added
Created `momence_sessions` table in CM Supabase project. Used for Momence-side session cross-check.
Migration: `MIGRATION-momence-sessions-table-2026-05-11.sql`
Note: This table will be superseded by the Phase 1 `momence_sessions` mirror table in RSO.

#### 2026-05-09 | CM | Phase 2 dedup; permissions; Mikela merge
Deduplication of existing cover requests. Permissions migration. Mikela teacher record merge.
Migrations: `MIGRATION-phase2-dedup-2026-05-09.sql`, `MIGRATION-permissions-2026-05-09.sql`, `PHASE2-MERGE-MIKELA-2026-05-09.sql`, `PHASE2-PRE-DEDUP-FIXUPS-2026-05-09.sql`

#### 2026-05-08 | CM | Phase 1 schema hardening and resilience improvements
Extended cover request handling, improved error resilience in cover processor.
Source: `CHANGELOG-2026-05-08-phase1-and-resilience.md`

#### 2026-05-07 | CM | Scheduled task setup; class dates and resolved classes
Set up Windows Task Scheduler for monitor runs. Added class date tracking and resolved-class backfill.
Migration: `MIGRATION-class-dates-and-resolved-classes-2026-05-07.sql`
Source: `CHANGELOG-2026-05-07-scheduled-task-setup.md`

#### 2026-04-23 | CM | Availability slots
Added `avail_slots` to cover schema.
Migration: `MIGRATION-avail-slots-2026-04-23.sql`
Source: `CHANGELOG-2026-04-23-avail-slots.md`

#### 2026-04-21 | CM | Coverage type classification feature
Added `coverage_type` (temporary/permanent/both) field. NLP parser updated. Dashboard filter added.
Migration: `MIGRATION-coverage-type-2026-04-21.sql`
Sign-off: `SIGNOFF-coverage-type-2026-04-21.md`

#### 2026-04-13 | CM | NLP sender fallback
Fallback logic for sender name extraction when WhatsApp DOM heuristic fails.
Source: `CHANGELOG-2026-04-13-nlp-sender-fallback.md`

#### 2026-04-08 | CM | Stage 1 schema — initial CM schema
Created: `cover_requests`, `cover_candidates`, `cover_notifications`, `whatsapp_channels`, `whatsapp_monitor_runs`, `discipline_mappings`, `system_config`. Extended `teachers` with `whatsapp_phone` and `contact_preference`.
Migration: `stage1/01_cover_schema.sql`

---

### Teacher Management

#### 2026-04-07 | TM | Baseline restore; trainee bookings user_id
Restored to stable baseline. Added `user_id` to `trainee_bookings`.
Migration: `migrations/2026-04-07-add-trainee-bookings-user-id.sql`
Source: `CHANGELOG-2026-04-07-baseline-restore.md`

#### 2026-04-06 | TM | Course modal refinement
UI refinements to course/booking modal.
Source: `CHANGELOG-2026-04-06-course-modal-refinement.md`

#### 2026-04-05 | TM | Trainee bookings; reject flow; admin backfill; v29
Added `resolveTeacherIdForCurrentUser()`, reject modal, admin backfill UI. Fixed null-id PATCH bug. Created v29 with defensive sign-in and stray overwrite removal.
Migration: `migrations/2026-04-05-add-teacher-photo-and-momence.sql`
Source: `CHANGELOG-2026-04-05-teacher-management.md`
