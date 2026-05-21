# Ritual Studio Ops — Master Documentation Index

**Canonical lookup for all active documentation across all four Ritual technology projects.**

A document is not considered created until this index is updated. If a document is not listed here, it does not officially exist. Two entries for the same topic means one is a duplicate — mark the older as `superseded` and consolidate.

Last updated: 2026-05-21 (Phase 0 scaffold)
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
| Merger Plan v2 | Ritual Studio Ops | `Ritual_Teacher_Management/Ritual_Studio_Ops_Merger_Plan_v2.md` | active | Move to `Ritual_Studio_Ops/docs/` after Phase 0 git setup |
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
| Merger plan prompt | TM | `Ritual_Teacher_Management/prompts/find_skills_for_merger.md` | legacy | Working note from merger planning; superseded by this programme |

**Migrations (TM)**

| Migration | Location | Applied |
|---|---|---|
| 2026-04-05: add teacher photo and momence fields | `Ritual_Teacher_Management/migrations/2026-04-05-add-teacher-photo-and-momence.sql` | Yes |
| 2026-04-07: add trainee-bookings user_id | `Ritual_Teacher_Management/migrations/2026-04-07-add-trainee-bookings-user-id.sql` | Yes |

**App versions (TM)**

| Version | File | Status |
|---|---|---|
| v31 | `Ritual_Teacher_Management/ritual-teacher-management31.html` | **Canonical** — use for Phase 2 lift-across |
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
| Phase 5 user admin design | CM | `Ritual_Cover_Management/PHASE-5-USER-ADMIN-DESIGN.md` | active | User admin design |
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
| Merger Plan v2 | RSO | *(move from TM folder)* | active | Move to `Ritual_Studio_Ops/docs/` |
| .env template | RSO | `Ritual_Studio_Ops/.env.template` | active | Environment configuration template |
| services/momence README | RSO | `Ritual_Studio_Ops/services/momence/README.md` | active | Momence code move instructions |
| services/cover README | RSO | `Ritual_Studio_Ops/services/cover/README.md` | active | Cover pipeline move instructions (Phase 3) |

**Tables-and-owners matrix** (updated each migration)

| Table | Created by | Phase | Owner |
|---|---|---|---|
| `teachers` | TM original | Pre-merger | TM (RSO from Phase 2) |
| `class_history` | TM original | Pre-merger | TM |
| `user_profiles` | TM original | Pre-merger | TM |
| `audit_log` | TM original | Pre-merger | TM |
| `trainee_bookings` | TM changelog 2026-04-05 | Pre-merger | TM |
| `cover_requests` | CM stage 1 | Pre-merger | CM |
| `cover_candidates` | CM | Pre-merger | CM |
| `cover_notifications` | CM | Pre-merger | CM |
| `whatsapp_channels` | CM stage 1 | Pre-merger | CM |
| `whatsapp_messages` | CM | Pre-merger | CM |
| `whatsapp_monitor_runs` | CM | Pre-merger | CM |
| `system_config` | CM stage 1 | Pre-merger | CM |
| `discipline_mappings` | CM | Pre-merger | CM → superseded by `disciplines` in Phase 1 |
| `disciplines` | RSO | Phase 1 | RSO |
| `studios` | RSO | Phase 1 | RSO — seed data: Palm Beach (active), Robina (active), Mermaid (`is_active = false`, closed/retired) |
| `momence_sessions` | RSO | Phase 1 (empty) / Phase 7 (filled) | RSO |
| `momence_members` | RSO | Phase 1 (empty) / Phase 7 (filled) | RSO |
| `momence_bookings` | RSO | Phase 1 (empty) / Phase 7 (filled) | RSO |
| `momence_sync_runs` | RSO | Phase 1 | RSO |
| LESSONS_LEARNED | RSO | `Ritual_Studio_Ops/docs/LESSONS_LEARNED.md` | active | |
| Merger Plan v2 | RSO | `Ritual_Studio_Ops/docs/Ritual_Studio_Ops_Merger_Plan_v2.md` | active | |
| .env template | RSO | `Ritual_Studio_Ops/.env.template` | active | Environment configuration template |
| services/momence README | RSO | `Ritual_Studio_Ops/services/momence/README.md` | active | Momence code move instructions |
| services/cover README | RSO | `Ritual_Studio_Ops/services/cover/README.md` | active | Cover pipeline move instructions (Phase 3) |

**Tables-and-owners matrix** (updated each migration)

| Table | Created by | Phase | Owner |
|---|---|---|---|
| `teachers` | TM original | Pre-merger | TM (RSO from Phase 2) |
| `class_history` | TM original | Pre-merger | TM |
| `user_profiles` | TM original | Pre-merger | TM |
| `audit_log` | TM original | Pre-merger | TM |
| `trainee_bookings` | TM changelog 2026-04-05 | Pre-merger | TM |
| `cover_requests` | CM stage 1 | Pre-merger | CM |
| `cover_candidates` | CM | Pre-merger | CM |
| `cover_notifications` | CM | Pre-merger | CM |
| `whatsapp_channels` | CM stage 1 | Pre-merger | CM |
| `whatsapp_messages` | CM | Pre-merger | CM |
| `whatsapp_monitor_runs` | CM | Pre-merger | CM |
| `system_config` | CM stage 1 | Pre-merger | CM |
| `discipline_mappings` | CM | Pre-merger | CM — superseded by `disciplines` in Phase 1 |
| `disciplines` | RSO | Phase 1 | RSO |
| `studios` | RSO | Phase 1 | RSO — seed data: Palm Beach (active), Robina (active), Mermaid (`is_active = false`, closed/retired) |
| `momence_sessions` | RSO | Phase 1 (empty) / Phase 7 (filled) | RSO |
| `momence_members` | RSO | Phase 1 (empty) / Phase 7 (filled) | RSO |
| `momence_bookings` | RSO | Phase 1 (empty) / Phase 7 (filled) | RSO |
| `momence_sync_runs` | RSO | Phase 1 | RSO |
