# Ritual Studio Ops — Master Documentation Index

**Canonical lookup for all active documentation across all four Ritual technology projects.**

A document is not considered created until this index is updated. If a document is not listed here, it does not officially exist. Two entries for the same topic means one is a duplicate — mark the older as `superseded` and consolidate.

Last updated: 2026-06-15 (reference data migration docs added; see 2026-05-23 CHANGELOG entry)
Maintained by: Ritual Studio Ops project (Claude as PM)

---

## How to read this index

| Column | Meaning |
|---|---|
| Status | `active` = current canon · `superseded` = replaced by another entry · `legacy` = pre-merger, archived |
| Owner | Which project owns this document |
| Location | Path relative to `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\` unless noted |

---

## 1. Merger & Programme Governance

| Document | Owner | Location | Status | Notes |
|---|---|---|---|---|
| Merger Plan v2 | Ritual Studio Ops | `Ritual_Studio_Ops/docs/Ritual_Studio_Ops_Merger_Plan_v2.md` | active | Moved from TM folder 2026-05-21 |
| Merger Plan v1 | Ritual Studio Ops | `Ritual_Teacher_Management/Ritual_Studio_Ops_Merger_Plan_v1.md` | superseded | Superseded by v2 same day (2026-05-14) |
| DOCS_INDEX (this file) | Ritual Studio Ops | `Ritual_Studio_Ops/docs/DOCS_INDEX.md` | active | Master index for all four projects |
| CHANGELOG | Ritual Studio Ops | `Ritual_Studio_Ops/docs/CHANGELOG.md` | active | Master changelog for all four projects |
| LESSONS_LEARNED | Ritual Studio Ops | `Ritual_Studio_Ops/docs/LESSONS_LEARNED.md` | active | Consolidated hard-won knowledge |

---

## 2. Teacher Management (TM)

| Document | Owner | Location | Status | Notes |
|---|---|---|---|---|
| Prompt Guide (Markdown) | TM | `Ritual_Teacher_Management/Ritual_Teacher_App_Prompt_Guide.md` | active | Critical technical constraints in Phase 2 of guide; use as Phase 2 reference |
| Prompt Guide (DOCX) | TM | `Ritual_Teacher_Management/Ritual_Teacher_App_Prompt_Guide.docx` | active | Same content as .md; keep both for accessibility |
| Business Improvement spec v15 | TM | `Ritual_Teacher_Management/Ritual Studios Business Improvement teacher management v15.txt` | active | Original requirements brief |
| Supabase schema snapshot 2026-04-06 | TM | `Ritual_Teacher_Management/Supabase schema 2026 04 06.txt` | legacy | Point-in-time snapshot; live schema in migrations |
| Teacher management styles | TM | `Ritual_Teacher_Management/Teacher management styles.md` | active | CSS design tokens and component style notes |
| Changelog 2026-04-05 | TM | `Ritual_Teacher_Management/CHANGELOG-2026-04-05-teacher-management.md` | legacy | Absorbed into master CHANGELOG |
| Changelog 2026-04-06 | TM | `Ritual_Teacher_Management/CHANGELOG-2026-04-06-course-modal-refinement.md` | legacy | Absorbed into master CHANGELOG |
| Changelog 2026-04-07 | TM | `Ritual_Teacher_Management/CHANGELOG-2026-04-07-baseline-restore.md` | legacy | Absorbed into master CHANGELOG |
| Investigation: teachers dropdown 2026-05-14 | TM | `Ritual_Teacher_Management/INVESTIGATION-teachers-dropdown-2026-05-14.md` | active | Exists in both TM and CM — CM copy is authoritative |
| Recommendations re id | TM | `Ritual_Teacher_Management/Recommendations re id.md` | legacy | Design note; content absorbed into LESSONS_LEARNED |
| Booking flow test | TM | `Ritual_Teacher_Management/BOOKING_FLOW_TEST.md` | active | Test plan for trainee booking flow |
| Booking test results | TM | `Ritual_Teacher_Management/BOOKING_TEST_RESULTS.md` | active | Execution results of above |
| Teacher Absences design spec | TM | `Ritual_Teacher_Management/Ritual Teacher Management/Teacher_Absences_Design.md` | active | Full design spec: data model, RLS, API pattern, UI layout, migration plan. Approved and implemented 2026-05-27. |
| Teacher Applications design spec | TM | `Ritual_Teacher_Management/Ritual Teacher Management/Teacher_Applications_Design.md` | active | Public teacher-application intake + Applicants review. Data model (status flag), RLS, Edge Functions, WhatsApp paused, import plan. rev 3, 2026-06-01. |
| Public application form | RSO | `Ritual_Studio_Ops/app/apply.html` | active | Public unauthenticated teacher application form + email-code verification. Calls submit-teacher-application and verify-application-otp. Deploy with Pages; link from website. |
| Merger plan prompt | TM | `Ritual_Teacher_Management/prompts/find_skills_for_merger.md` | legacy | Working note from merger planning; superseded by this programme |

**Migrations (TM)**

| Migration | Location | Applied |
|---|---|---|
| 2026-04-05: add teacher photo and momence fields | `Ritual_Teacher_Management/migrations/2026-04-05-add-teacher-photo-and-momence.sql` | Yes |
| 2026-04-07: add trainee-bookings user_id | `Ritual_Teacher_Management/migrations/2026-04-07-add-trainee-bookings-user-id.sql` | Yes |
| 2026-05-27: teacher_absences table, indexes, RLS | `Ritual_Studio_Ops/migrations/2026-05-27-teacher-absences.sql` | Yes — applied via Supabase MCP 2026-05-27 |
| 2026-06-01: teacher applications (columns, application_otps, config seed) | `Ritual_Studio_Ops/migrations/2026-06-01-teacher-applications.sql` | Yes — applied via Supabase MCP 2026-06-01 |
| 2026-06-01: teacher-cvs storage bucket + read policy | `Ritual_Studio_Ops/migrations/2026-06-01-teacher-cvs-bucket.sql` | Yes — applied via Supabase MCP 2026-06-01 |

**App versions (TM)**

| Version | File | Status |
|---|---|---|
| v31 | `Ritual_Teacher_Management/ritual-teacher-management31.html` | Legacy — RSO Phase 4 legacy banner added; superseded by RSO v1 |
| v30 | `Ritual_Teacher_Management/ritual-teacher-management30.html` | Legacy |
| v30 (copy) | `Ritual_Teacher_Management/ritual-teacher-management30 - Copy.html` | Legacy |

---

## 3. Cover Management (CM)

| Document | Owner | Location | Status | Notes |
|---|---|---|---|---|
| README | CM | `Ritual_Cover_Management/README.md` | active | Project overview |
| Architecture | CM | `Ritual_Cover_Management/ARCHITECTURE.md` | active | Full system architecture; key reference for Phase 3 |
| Schema | CM | `Ritual_Cover_Management/SCHEMA.md` | active | Database schema documentation |
| Index | CM | `Ritual_Cover_Management/Index.md` | active | CM's own document index |
| Developer guide | CM | `Ritual_Cover_Management/DEVELOPER.md` | active | Developer onboarding |
| Deploy guide | CM | `Ritual_Cover_Management/DEPLOY.md` | active | Deployment instructions |
| Setup guide | CM | `Ritual_Cover_Management/SETUP.md` | active | Initial setup |
| Handoff: start here | CM | `Ritual_Cover_Management/HANDOFF-START-HERE.md` | active | Onboarding handoff |
| Handoff: coverage type | CM | `Ritual_Cover_Management/HANDOFF-coverage-type-execution.md` | active | Coverage type feature handoff |
| Help | CM | `Ritual_Cover_Management/HELP.md` | active | Operator help guide |
| Quick reference | CM | `Ritual_Cover_Management/QUICKREF.md` | active | Quick command reference |
| Troubleshooting | CM | `Ritual_Cover_Management/TROUBLESHOOTING.md` | active | Known issues and fixes |
| Workflow summary | CM | `Ritual_Cover_Management/WORKFLOW-SUMMARY.md` | active | End-to-end workflow overview |
| Nested messages | CM | `Ritual_Cover_Management/Nested_Messages.md` | active | Quoted/threaded message handling |
| WhatsApp changelog | CM | `Ritual_Cover_Management/Changelog WhatsApp.md` | active | WhatsApp-specific change log |
| Changelog 2026-04-13 | CM | `Ritual_Cover_Management/CHANGELOG-2026-04-13-nlp-sender-fallback.md` | legacy | Absorbed into master CHANGELOG |
| Changelog 2026-04-23 | CM | `Ritual_Cover_Management/CHANGELOG-2026-04-23-avail-slots.md` | legacy | Absorbed into master CHANGELOG |
| Changelog 2026-05-07 | CM | `Ritual_Cover_Management/CHANGELOG-2026-05-07-scheduled-task-setup.md` | legacy | Absorbed into master CHANGELOG |
| Changelog 2026-05-08 | CM | `Ritual_Cover_Management/CHANGELOG-2026-05-08-phase1-and-resilience.md` | legacy | Absorbed into master CHANGELOG |
| Changelog 2026-05-09 | CM | `Ritual_Cover_Management/CHANGELOG-2026-05-09.md` | legacy | Absorbed into master CHANGELOG |
| Changelog 2026-05-11 | CM | `Ritual_Cover_Management/CHANGELOG-2026-05-11-momence-sessions-table.md` | legacy | Absorbed into master CHANGELOG |
| Changelog 2026-05-16 | CM | `Ritual_Cover_Management/CHANGELOG-2026-05-16.md` | legacy | Absorbed into master CHANGELOG |
| Changelog 2026-05-17 | CM | `Ritual_Cover_Management/CHANGELOG-2026-05-17.md` | legacy | Absorbed into master CHANGELOG |
| Changelog 2026-05-20 (dashboard) | CM | `Ritual_Cover_Management/CHANGELOG-dashboard-spinning-fix-20260520.md` | legacy | Absorbed into master CHANGELOG |
| Investigation: teachers dropdown | CM | `Ritual_Cover_Management/INVESTIGATION-teachers-dropdown-2026-05-14.md` | active | **Authoritative copy** (also exists in TM; CM copy is canonical) |
| Session log 2026-05-08 | CM | `Ritual_Cover_Management/SESSION-LOG-2026-05-08-evening.md` | legacy | Working session log |
| Phase 2 dedup design | CM | `Ritual_Cover_Management/PHASE-2-DEDUP-DESIGN.md` | active | Design doc for CM dedup phase |
| Phase 3 dashboard design | CM | `Ritual_Cover_Management/PHASE-3-DASHBOARD-DESIGN.md` | active | Dashboard design spec |
| Phase 4 offer matching design | CM | `Ritual_Cover_Management/PHASE-4-OFFER-MATCHING-DESIGN.md` | active | Offer matching design |
| Phase 5 user admin design | CM | `Ritual_Cover_Management/PHASE-5-USER-ADMIN-DESIGN.md` | superseded | In-Portal User Admin (CM-feature scheme; see PHASE-NUMBERING.md). Carries a 2026-06-02 revision notice: targets the merged app now, 5.1 UI already built, 5.0+5.2 still to do. Re-spec in progress |
| Phase numbering (disambiguation) | RSO | `Ritual_Studio_Ops/docs/PHASE-NUMBERING.md` | active | Canonical map of the four overlapping "Phase N" schemes. Cite when a phase number is ambiguous |
| RBAC matrix & unification | RSO | `Ritual_Studio_Ops/docs/RBAC-MATRIX.md` | active | Role × permission matrix; capability→permission mapping; how the two authz regimes were merged |
| User Admin build spec | RSO | `Ritual_Studio_Ops/docs/USER-ADMIN-BUILD-SPEC.md` | active | Revised Phase 5 (User Admin) 5.0/5.1/5.2 build spec, grounded in live DB |
| User Admin handover | RSO | `Ritual_Studio_Ops/docs/USER-ADMIN-HANDOVER-2026-06-03.md` | active | What was applied to the DB vs staged in the app; pending browser-test + push |
| User Admin test plan | RSO | `Ritual_Studio_Ops/docs/USER-ADMIN-TEST-PLAN.md` | active | Re-runnable SQL + browser tests for the RBAC/User-Admin work |
| Migration: RBAC backbone | RSO | `Ritual_Studio_Ops/migrations/2026-06-02-rbac-unification-backbone.sql` | applied | Catalogue extension + leaf grants + override table + per-user resolver + helper (applied 2026-06-02) |
| Migration: User Admin RPCs + RLS | RSO | `Ritual_Studio_Ops/migrations/2026-06-02-user-admin-rpcs-and-rls.sql` | applied | admin RPCs + user-admin RLS switched to admin.users.manage (applied 2026-06-02) |
| Migration: User Admin harden grants | RSO | `Ritual_Studio_Ops/migrations/2026-06-02-user-admin-harden-grants.sql` | applied | search_path + revoke anon EXECUTE (applied 2026-06-02) |
| Migration: user_profiles RLS backfill | RSO | `Ritual_Studio_Ops/migrations/2026-06-02-user-profiles-admin-rls-backfill.sql` | parity | Records pre-existing live user_profiles policies (documentation/parity only) |
| 5.2 overrides UI snippet | RSO | `Ritual_Studio_Ops/app/_user-admin-5.2-overrides.snippet.js` | ready | Per-user permission override tree UI, validated; ready to integrate + browser-test |
| Phases quick invoke | CM | `Ritual_Cover_Management/PHASES-quick-invoke.md` | active | Quick command reference per phase |
| Plan: coverage type | CM | `Ritual_Cover_Management/PLAN-coverage-type-feature.md` | active | Feature plan |
| Plan: phase 4 offer matching | CM | `Ritual_Cover_Management/PLAN-phase4-offer-matching-2026-05-16.md` | active | Feature plan |
| Sign-off: coverage type | CM | `Ritual_Cover_Management/SIGNOFF-coverage-type-2026-04-21.md` | active | Feature acceptance sign-off |
| Skill: coverage type classification | CM | `Ritual_Cover_Management/SKILL-coverage-type-classification.md` | active | Claude skill file for NLP |
| Skill: estimate class count | CM | `Ritual_Cover_Management/SKILL-estimate-class-count.md` | active | Claude skill file for class count |
| Project memory | CM | `Ritual_Cover_Management/project_cover_management.md` | legacy | Working memory; content absorbed into this programme |

**Migrations (CM — applied in order)**

| Migration | File | Applied |
|---|---|---|
| Stage 1 schema | `stage1/01_cover_schema.sql` | Yes |
| Coverage type 2026-04-21 | `MIGRATION-coverage-type-2026-04-21.sql` | Yes |
| Avail slots 2026-04-23 | `MIGRATION-avail-slots-2026-04-23.sql` | Yes |
| Class dates & resolved 2026-05-07 | `MIGRATION-class-dates-and-resolved-classes-2026-05-07.sql` | Yes |
| Permissions 2026-05-09 | `MIGRATION-permissions-2026-05-09.sql` | Yes |
| Phase 2 dedup 2026-05-09 | `MIGRATION-phase2-dedup-2026-05-09.sql` | Yes |
| Momence sessions table 2026-05-11 | `MIGRATION-momence-sessions-table-2026-05-11.sql` | Yes |
| RLS phase1 permissions 2026-05-17 | `MIGRATION-rls-phase1-permissions-tables-2026-05-17.sql` | Yes |
| WhatsApp message timestamp 2026-05-17 | `MIGRATION-whatsapp-message-timestamp-2026-05-17.sql` | Yes |
| ADD: anon-read policy teachers | `migrations/ADD-anon-read-policy-teachers.sql` | **Review before Phase 1** — this policy is being replaced |
| ADD: quoted-reply to whatsapp_messages | `migrations/ADD-quoted-reply-to-whatsapp-messages.sql` | Yes |
| FIX: JSONB string encoding | `migrations/FIX-jsonb-string-encoding-cover-requests.sql` | Yes |
| Phase 2 pre-dedup fixups | `PHASE2-PRE-DEDUP-FIXUPS-2026-05-09.sql` | Yes |
| Phase 2 Mikela merge | `PHASE2-MERGE-MIKELA-2026-05-09.sql` | Yes |

---

## 4. Momence_data

> **Note:** Momence_data files live at `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\` — different OneDrive account. This is the MOMENCE_DATA_DIR. The code will move to `Ritual_Studio_Ops/services/momence/` in Phase 0 (pending MFPL OneDrive mount). The data folders stay here permanently.

**All Momence code and canonical documentation now lives in `Ritual_Studio_Ops/services/momence/`. MFPL OneDrive mounted and copy completed 2026-05-21.**

| Document | Owner | Location | Status | Notes |
|---|---|---|---|---|
| Scraping wisdom | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/Momence_data_scraping_wisdom.md` | **active — canonical** | Consolidated here; Dashboard copy superseded |
| Technical details | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/TECHNICAL_DETAILS.md` | **active — canonical** | Consolidated here; Dashboard copy superseded |
| Skill usage guide | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/MOMENCE_SKILL_USAGE_GUIDE.md` | **active — canonical** | |
| API v2 reference | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/Momence_API_v2_Reference.md` | **active — canonical** | |
| Cookie auth reference | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/Momence_Cookie_Auth_Reference.md` | **active — canonical** | |
| Pipeline maintenance guide | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/PIPELINE_MAINTENANCE_GUIDE.md` | **active — canonical** | |
| Handover notes | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/HANDOVER_NOTES.md` | **active — canonical** | |
| Installation setup | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/INSTALLATION_SETUP_GUIDE.md` | **active — canonical** | |
| Data cleanup rules | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/DATA_CLEANUP_RULES.md` | **active — canonical** | |
| Env integration summary | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/ENV_INTEGRATION_SUMMARY.md` | **active — canonical** | |
| Quick start | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/QUICK_START.md` | **active — canonical** | |
| Run now | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/RUN_NOW.md` | **active — canonical** | |
| Verification checklist | RSO (was Momence_data) | `Ritual_Studio_Ops/services/momence/docs/VERIFICATION_CHECKLIST.md` | **active — canonical** | |
| Scraping wisdom (Dashboard copy) | Ritual Dashboard | `Ritual Dashboard/docs/Momence Scrape documentation/Momence_data_scraping_wisdom.md` | **superseded** | Canonical copy is in services/momence/docs/ |
| Technical details (Dashboard copy) | Ritual Dashboard | `Ritual Dashboard/docs/Momence Scrape documentation/TECHNICAL_DETAILS.md` | **superseded** | Canonical copy is in services/momence/docs/ |

---

## 5. Ritual Dashboard

> Dashboard remains a downstream analytics consumer. It is not rewritten as part of this programme. Its documentation stays where it is; key docs are indexed here for completeness.

| Document | Owner | Location | Status | Notes |
|---|---|---|---|---|
| Project plan (v1.2) | Dashboard | `Ritual Dashboard/docs/` | active | Dashboard programme plan |
| KPI library (v1.1) | Dashboard | `Ritual Dashboard/docs/` | active | KPI definitions and sources |
| Momence scraping docs | Dashboard | `Ritual Dashboard/docs/Momence Scrape documentation/` | superseded | See Momence_data section above — consolidate |

---

## 6. Reference & Brand

| Document | Owner | Location | Status | Notes |
|---|---|---|---|---|
| Ritual Brand guidelines | Cross-project | `Ritual_Apps/RITUAL_BRAND.md` | active | Brand colours, fonts, voice |
| Xero API integration guide | TM | `Ritual_Teacher_Management/Xero API Integration Architecture and Implementation Guide.docx` | legacy | Not in scope for this programme |
| Firebase schema analysis | Legacy migration | `Ritual_Apps/FIREBASE_SCHEMA_ANALYSIS.md` | legacy | Pre-Supabase migration artefact |
| Firebase-to-Supabase mapping | Legacy migration | `Ritual_Apps/FIREBASE_TO_SUPABASE_MAPPING.md` | legacy | Pre-Supabase migration artefact |

---

## 7. Ritual Studio Ops (merged app — this project)

| Document | Owner | Location | Status | Notes |
|---|---|---|---|---|
| README | RSO | `Ritual_Studio_Ops/docs/README.md` | active | Four-project landscape for new starters |
| DOCS_INDEX (this file) | RSO | `Ritual_Studio_Ops/docs/DOCS_INDEX.md` | active | |
| CHANGELOG | RSO | `Ritual_Studio_Ops/docs/CHANGELOG.md` | active | |
| LESSONS_LEARNED | RSO | `Ritual_Studio_Ops/docs/LESSONS_LEARNED.md` | active | |
| Merger Plan v2 | RSO | `Ritual_Studio_Ops/docs/Ritual_Studio_Ops_Merger_Plan_v2.md` | active | Moved from TM folder 2026-05-21 |
| .env template | RSO | `Ritual_Studio_Ops/.env.template` | active | Environment configuration template |
| Merged app v2 (LIVE) | RSO | `Ritual_Studio_Ops/app/ritual-studio-ops-v2.html` | active | Teachers + Cover. The live merged app. ("Phase 5 build" here = the v2 build-iteration scheme C, NOT the merger Phase 5 or the User-Admin Phase 5 — see PHASE-NUMBERING.md.) Includes teacher absence tracking, per-teacher panel, global absences view, on-leave sidebar pill, CRUD modal, soft-delete archive, and the existing user-management settings page. |
| Management Portal (LIVE) | RSO | `Ritual_Studio_Ops/app/index.html` | active | Launcher hub for the new system; carries the emblem badge. Adapted from the legacy CM portal 2026-05-24. |
| Finance & Cashflow dashboard | RSO | `Ritual_Studio_Ops/app/finance-cashflow.html` | active | v1 (2026-05-29). Static client-side cashflow dashboard opened from the portal Finance tile. Embeds Xero Stripe-settlement actuals Jul 2025 - Feb 2026; 13-week rolling forecast with editable assumptions. No auth gate yet (see PORTAL-DEVELOPER.md security note). |
| Merged app v1 | RSO | `Ritual_Apps/RSO_archived_duplicates_2026-05-24/ritual-studio-ops-v1.html` | archived | Superseded by v2; truncated/corrupt. Moved to the archive folder on 2026-05-24. |
| services/momence README | RSO | `Ritual_Studio_Ops/services/momence/README.md` | active | Momence code move instructions |
| services/cover README | RSO | `Ritual_Studio_Ops/services/cover/README.md` | active | Cover pipeline move instructions (Phase 3) |
| Test suite Phase 2 | RSO | `Ritual_Studio_Ops/scripts/test_phase2.py` | active | 37 checks — merged shell conventions |
| Test suite Phase 3 | RSO | `Ritual_Studio_Ops/scripts/test_phase3.py` | active | 65 checks — cover pipeline re-point |
| Test suite Phase 4 | RSO | `Ritual_Studio_Ops/scripts/test_phase4.py` | active | 24 checks — write-enable and legacy banners |
| Test suite Phase 5 | RSO | `Ritual_Studio_Ops/scripts/test_phase5.py` | active | 28 checks — reconcile script (merger-programme Phase 5, scheme A — see PHASE-NUMBERING.md) |
| Reconcile script | RSO | `Ritual_Studio_Ops/scripts/reconcile.py` | active | Daily parallel-run health check; run once per day during the merger Phase 5 (scheme A) soak |
| Reconcile reports | RSO | `Ritual_Studio_Ops/scripts/reconcile_reports/` | active | Daily plain-text reports written by reconcile.py |
| Source-of-truth map | RSO | `Ritual_Studio_Ops/docs/SOURCE_OF_TRUTH.md` | active | Which file backs which screen. Read before requesting changes to any dashboard or portal. |
| Navigation map | RSO | `Ritual_Studio_Ops/docs/NAVIGATION.md` | active | Diagram of how portals, dashboards and external platforms link, plus the Phase 6 Pages consolidation plan. |
| Setup audit (2026-05-24) | RSO | `Ritual_Studio_Ops/docs/AUDIT-RSO-2026-05-24.md` | active | Latest setup audit with severity-rated findings. |
| Migration 2026-05-22: source on cover_requests | RSO | `Ritual_Studio_Ops/migrations/2026-05-22-add-source-to-cover-requests.sql` | active | Adds the `source` column distinguishing whatsapp vs manual cover requests. |
| Migration 2026-05-27: teacher_absences | RSO | `Ritual_Studio_Ops/migrations/2026-05-27-teacher-absences.sql` | active | Creates `teacher_absences` table, trigger, 3 partial indexes, 5 RLS policies. Applied 2026-05-27 via Supabase MCP. |
| Edge Function: parse-cover-request | RSO | Supabase project rfjygyqijwgkmxboddup (deployed via MCP) | active | Called by the v2 Manual Cover Request modal. JWT-verified. No local source file in the repo. |
| Migration 2026-05-22: reference tables | RSO | `G:\Shared drives\RITUAL MASTER DRIVE\Claude Project 20260322\Ritual Studios\migrations\2026-05-22-reference-tables.sql` | applied | Creates membership_types, class_group_mappings; adds teachers.hourly_cost. Applied 2026-05-22. |
| Migration 2026-05-23: locations, rooms, pay rates | RSO | `G:\Shared drives\RITUAL MASTER DRIVE\Claude Project 20260322\Ritual Studios\migrations\2026-05-23-locations-rooms-pay-rates.sql` | applied | Creates locations, rooms, location_aliases, teacher_pay_rate_tiers; adds teachers.default_pay_rate. Applied 2026-05-23. |
| Migration 2026-05-23b: drop check constraints | RSO | `G:\Shared drives\RITUAL MASTER DRIVE\Claude Project 20260322\Ritual Studios\migrations\2026-05-23b-drop-ref-check-constraints.sql` | applied | Drops over-restrictive CHECK constraints on membership_types.membership_type and class_group_mappings.class_group. Applied 2026-05-23. |
| Reference data migration summary | RSO | `G:\Shared drives\RITUAL MASTER DRIVE\Claude Project 20260322\Ritual Studios\migrations\MIGRATION_SUMMARY.md` | active | Full reference for all reference-data tables, migration run order, seed script usage, classify.py behaviour, location alias model, and outstanding items. Last updated 2026-05-23. |
| Seed script: reference tables | RSO | `G:\Shared drives\RITUAL MASTER DRIVE\Claude Project 20260322\Ritual Studios\scripts\seed_reference_tables.py` | active | Idempotent seed for all 8 reference data sections. Supports --dry-run and --only TABLE flags. Requires SUPABASE_SERVICE_KEY env var (set per session only; do not hardcode). |

**Tables-and-owners matrix** (updated each migration — 2026-05-merged-v1.sql)

| Table | Created by | Phase | Owner | Notes |
|---|---|---|---|---|
| `teachers` | TM original | Pre-merger | TM (RSO from Phase 2) | 79 rows. RLS on. |
| `class_history` | TM original | Pre-merger | TM | 0 rows. RLS on. |
| `user_profiles` | TM original | Pre-merger | TM | 6 rows. RLS on. |
| `audit_log` | TM original | Pre-merger | TM | 22 rows. RLS on. |
| `permissions` | CM migration 2026-05-09 | Pre-merger | TM/CM shared | 26 rows. RLS on. |
| `role_permissions` | CM migration 2026-05-09 | Pre-merger | TM/CM shared | 22 rows. RLS on. |
| `training_courses` | TM (momence_courses_sync.py) | Pre-merger | TM | 6 rows. RLS off — review. |
| `trainee_enrollments` | TM | Pre-merger | TM | 18 rows. RLS off — review. |
| `timeslots` | TM | Pre-merger | TM | 12 rows. RLS off — review. |
| `trainee_bookings` | TM changelog 2026-04-05 | Pre-merger | TM | 12 rows. RLS off — review. |
| `cover_requests` | CM stage 1 | Pre-merger | CM | 70 rows. RLS off — review. |
| `cover_candidates` | CM | Pre-merger | CM | 0 rows. RLS off — review. |
| `cover_notifications` | CM | Pre-merger | CM | 0 rows. RLS off — review. |
| `whatsapp_channels` | CM stage 1 | Pre-merger | CM | 4 rows. RLS off — review. |
| `whatsapp_messages` | CM | Pre-merger | CM | 70 rows. RLS off — review. |
| `whatsapp_monitor_runs` | CM | Pre-merger | CM | 204 rows. RLS off — review. |
| `system_config` | CM stage 1 | Pre-merger | CM | 6 rows. RLS off — review. |
| `discipline_mappings` | CM | Pre-merger | CM | 6 rows. Superseded by `disciplines`. Kept for backwards compat. |
| `disciplines` | RSO | Phase 1 (2026-05-21) | RSO | Canonical taxonomy. 5 rows seeded. RLS on. |
| `studios` | RSO | Phase 1 (2026-05-21) | RSO | Canonical studios. Seed: Palm Beach (active), Robina (active), Mermaid (`is_active = false`, closed/retired). RLS on. |
| `momence_sessions` | CM (MIGRATION-momence-sessions-table-2026-05-11) | Pre-merger — **already populated** | RSO | 7,365 rows. RLS on. Phase 7 session sync is already running. |
| `momence_members` | RSO | Phase 1 (2026-05-21) — empty placeholder | RSO | 0 rows. Filled in Phase 7. RLS on. |
| `momence_bookings` | RSO | Phase 1 (2026-05-21) — empty placeholder | RSO | 0 rows. Filled in Phase 7. RLS on. |
| `momence_sync_runs` | RSO | Phase 1 (2026-05-21) | RSO | Audit log for Phase 7 sync jobs. RLS on. |
| `teacher_absences` | TM | 2026-05-27 (migration 2026-05-26-teacher-absences.sql) | TM | 0 rows. RLS on (5 policies). Soft-delete via `deleted_at`. |
| `membership_types` | external workstream (Data workbook, 2026-05-22) | Pre-existing | Unassigned - RSO Settings -> Reference Data | 187 rows. RLS on. Comment references the Data workbook for Ritual analysis. Needs documented owner. |
| `class_group_mappings` | external workstream (Data workbook, 2026-05-22) | Pre-existing | Unassigned | 87 rows. RLS on. Class-name to coarse-group mapping. Needs documented owner. |
| `locations` | external workstream | Pre-existing | Unassigned | 3 rows. RLS on. Overlaps conceptually with `studios` - taxonomy reconciliation pending. |
| `rooms` | external workstream | Pre-existing | Unassigned | 5 rows. RLS on. |
| `location_aliases` | external workstream | Pre-existing | Unassigned | 8 rows. RLS on. |
| `teacher_pay_rate_tiers` | external workstream | Pre-existing | Unassigned | 8 rows. RLS on. |
