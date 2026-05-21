# Ritual Studio Ops — Master Changelog

All significant changes to schema, code, configuration, and documentation across all four Ritual technology projects, in reverse chronological order.

Individual project changelogs are NOT the authoritative record from Phase 0 onwards — this file is. Add a one-line entry here first, then write detail in the project-level file if needed.

Format: `YYYY-MM-DD | Project | Summary | Files changed`

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
