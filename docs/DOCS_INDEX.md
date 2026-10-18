# Ritual Studios — Master Documentation Index

**Canonical lookup for all documentation across the Ritual technology estate:** Studio Ops (merged Teacher + Cover), Cover Management, Teacher Management (legacy), the Analytics Dashboard, Momence_data, Campaign Planning, Finance & Cashflow and CleanSweep.

A document is not considered created until this index is updated. If a document is not listed here, it does not officially exist. Two entries for the same topic means one is a duplicate — mark the older as `superseded` and consolidate, or archive it (section 13).

Last updated: **2026-10-18 (second pass)** — full documentation audit: superseded and duplicate documents archived, Momence canonical location corrected, previously unindexed folders added (programme documents, Campaign Planning, CleanSweep, Ritual_Apps root), user guides and video prompts added, and every row in Appendices A and B given a status. Audit report: `Ritual_Apps/Docs/Documentation_Audit_2026-10-18.md`.
Maintained by: Ritual Studio Ops project (Claude as PM, for Mark Fellows)

> **Not covered:** `G:\Shared drives\RITUAL MASTER DRIVE\Claude Project 20260322\Ritual Studios` could not be reached from the workspace on 2026-10-18. Rows that point there are carried forward unverified.

---

## Start here

| You are… | Read first |
|---|---|
| A member of staff, teacher or owner | `Ritual_Apps/Docs/User_Guides/README.md` (section 9) |
| A developer making a change | `Ritual_Apps/RSO_DEPLOYMENT_MAP.md`, then `Ritual_Studio_Ops/docs/SOURCE_OF_TRUTH.md` (read the 2026-10-18 correction in section 7 below), then `LESSONS_LEARNED.md` |
| Looking after the overnight data | `Momence_data/PIPELINE_MAINTENANCE_GUIDE.md` (section 4) |
| Reviewing strategy and progress | `Ritual_Apps/Docs/Ritual_Work_Review_2026-10-14.md` and `Ritual_Phase2_Proposal_2026-10-14.md` (section 8) |
| Looking for something old | The archive manifests (section 13) |

---

## How to read this index

| Column | Meaning |
|---|---|
| Status | `active` = current canon · `historical` = accurate record of past work, not a guide to the present · `superseded` = replaced by another entry, kept in place · `archived` = moved to a `_Doc_Archive` folder (section 13) · `legacy` = belongs to an app being retired · `to confirm` = owner decision needed |
| Owner | Which project owns this document |
| Location | Path relative to `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\` unless it starts with `Ritual Dashboard/` (`C:\Users\markj\OneDrive\Desktop\`) or `Momence_data/` (`C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\`) |

---

## 1. Merger & Programme Governance

| Document | Owner | Location | Status | Notes |
|---|---|---|---|---|
| Merger Plan v2 | Ritual Studio Ops | `Ritual_Studio_Ops/docs/Ritual_Studio_Ops_Merger_Plan_v2.md` | active | Moved from TM folder 2026-05-21 |
| Merger Plan v1 | Ritual Studio Ops | `_Doc_Archive/2026-10-18/Ritual_Teacher_Management/Ritual_Studio_Ops_Merger_Plan_v1.md` | archived | Superseded by v2 same day (2026-05-14). Archived 2026-10-18; the identical v2 copy that sat in the TM folder was archived at the same time |
| DOCS_INDEX (this file) | Ritual Studio Ops | `Ritual_Studio_Ops/docs/DOCS_INDEX.md` | active | Master index for the whole estate |
| Documentation audit 2026-10-18 | Ritual Studio Ops | `Docs/Documentation_Audit_2026-10-18.md` | active | Findings, archive list, decisions needed, maintenance rules |
| Phase numbering | Ritual Studio Ops | `Ritual_Studio_Ops/docs/PHASE-NUMBERING.md` | active | Which "Phase N" scheme a document means |
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
| Investigation: teachers dropdown 2026-05-14 (TM copy) | TM | `_Doc_Archive/2026-10-18/Ritual_Teacher_Management/INVESTIGATION-teachers-dropdown-2026-05-14.md` | archived | Non-canonical copy; the CM copy is authoritative (section 3) |
| Recommendations re id | TM | `_Doc_Archive/2026-10-18/Ritual_Teacher_Management/Recommendations re id.md` | archived | Design note; content absorbed into LESSONS_LEARNED |
| Booking flow test | TM | `Ritual_Teacher_Management/BOOKING_FLOW_TEST.md` | active | Test plan for trainee booking flow |
| Booking test results | TM | `Ritual_Teacher_Management/BOOKING_TEST_RESULTS.md` | active | Execution results of above |
| Teacher Absences design spec | TM | `Ritual_Teacher_Management/Ritual Teacher Management/Teacher_Absences_Design.md` | active | Full design spec: data model, RLS, API pattern, UI layout, migration plan. Approved and implemented 2026-05-27. |
| Teacher Applications design spec | TM | `Ritual_Teacher_Management/Ritual Teacher Management/Teacher_Applications_Design.md` | active | Public teacher-application intake + Applicants review. Data model (status flag), RLS, Edge Functions, WhatsApp paused, import plan. rev 3, 2026-06-01. |
| Public application form | RSO | `Ritual_Studio_Ops/app/apply.html` | active | Public unauthenticated teacher application form + email-code verification. Calls submit-teacher-application and verify-application-otp. Deploy with Pages; link from website. |
| Merger plan prompt | TM | `_Doc_Archive/2026-10-18/Ritual_Teacher_Management/prompts/find_skills_for_merger.md` | archived | Working note from merger planning |
| Pre-merger RSO stub docs | TM | `_Doc_Archive/2026-10-18/Ritual_Teacher_Management/Ritual_Studio_Ops-Legacy/docs/` | archived | Stub CHANGELOG, DOCS_INDEX, LESSONS_LEARNED (May 2026), superseded by `Ritual_Studio_Ops/docs/` |
| Teacher-app CLAUDE.md | TM | `Ritual_Teacher_Management/CLAUDE.md` | active | Working instructions for sessions on the legacy app |
| Legacy read-me | TM | `Ritual_Teacher_Management/_READ_ME_FIRST_LEGACY.md` | active | Warns that this folder is legacy |
| Cover change prompt template | TM | `Ritual_Teacher_Management/RSO_Cover_Change_Prompt_Template.md` | active | Change-prompt template |
| Portal login change prompt (TM copy, 12 Jun) | TM | `Ritual_Teacher_Management/RSO_Portal_Login_Change_Prompt.md` | to confirm | Differs from, and is newer than, `Ritual_Apps/RSO_Portal_Login_Change_Prompt.md` (2 Jun). Owner to decide which is canonical |
| Changelog 2026-05-26 (portal and access) | TM | `Ritual_Teacher_Management/CHANGELOG-2026-05-26-portal-and-access.md` | historical | |

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
| Index | CM | `Ritual_Cover_Management/Index.md` | superseded | CM's own index (last updated 2026-05-16). This master index takes precedence |
| Developer guide | CM | `Ritual_Cover_Management/DEVELOPER.md` | active | Developer onboarding |
| Deploy guide | CM | `Ritual_Cover_Management/DEPLOY.md` | active | Deployment instructions |
| Setup guide | CM | `Ritual_Cover_Management/SETUP.md` | active | Initial setup |
| Handoff: start here | CM | `Ritual_Cover_Management/HANDOFF-START-HERE.md` | active | Onboarding handoff |
| Handoff: coverage type | CM | `Ritual_Cover_Management/HANDOFF-coverage-type-execution.md` | active | Coverage type feature handoff |
| Help | CM | `Ritual_Cover_Management/HELP.md` | active | Plain-English orientation for operators. Monitor schedule corrected to hourly on 2026-10-18. Staff should use User Guide 04 |
| Quick reference | CM | `Ritual_Cover_Management/QUICKREF.md` | active | Quick command reference |
| Troubleshooting | CM | `Ritual_Cover_Management/TROUBLESHOOTING.md` | active | Known issues and fixes |
| Workflow summary | CM | `Ritual_Cover_Management/WORKFLOW-SUMMARY.md` | historical | End-to-end workflow as at 2026-04-20 (before offer matching). Current process: User Guide 04 and `docs/Cover_Process_Swimlane.svg` |
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
| Session log 2026-05-08 | CM | `_Doc_Archive/2026-10-18/Ritual_Cover_Management/SESSION-LOG-2026-05-08-evening.md` | archived | Working session log |
| Staff training guide (June 2026) | CM | `_Doc_Archive/2026-10-18/Ritual_Cover_Management/docs/Cover_Dashboard_Training_Guide.md` | archived | Superseded by `Docs/User_Guides/04_Cover_Management.md`, which carries its content forward and reflects the dashboard changes of 22 June 2026 |
| Cover process swimlane | CM | `Ritual_Cover_Management/docs/Cover_Process_Swimlane.svg` | active | Full process diagram with offers and rejections. Shows the earlier two-hourly monitor schedule; now hourly |
| Teacher mobile concepts | CM | `Ritual_Cover_Management/docs/Teacher_Mobile_Concepts.svg` | historical | Design concepts behind `teacher_schedule.html` |
| Momence teacher sync | CM | `Ritual_Cover_Management/docs/MOMENCE_TEACHER_SYNC.md` | active | Daily 07:45 teacher sync from Momence |
| Prompt: contact data-quality table | CM | `Ritual_Cover_Management/docs/PROMPT-contact-data-quality-table.md` | to confirm | Build prompt; not known to be built |
| Phase 2 dedup design | CM | `Ritual_Cover_Management/PHASE-2-DEDUP-DESIGN.md` | historical | Shipped; DB-level dedup added 2026-06-27 |
| Phase 3 dashboard design | CM | `Ritual_Cover_Management/PHASE-3-DASHBOARD-DESIGN.md` | historical | Shipped |
| Phase 4 offer matching design | CM | `Ritual_Cover_Management/PHASE-4-OFFER-MATCHING-DESIGN.md` | historical | Shipped 2026-06-02 |
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
| Plan: phase 4 offer matching | CM | `Ritual_Cover_Management/PLAN-phase4-offer-matching-2026-05-16.md` | historical | Feature plan; revised 2026-06-02 and shipped. Backup copies in `backups/phase4-2026-06-02/` |
| Sign-off: coverage type | CM | `Ritual_Cover_Management/SIGNOFF-coverage-type-2026-04-21.md` | active | Feature acceptance sign-off |
| Skill: coverage type classification | CM | `Ritual_Cover_Management/SKILL-coverage-type-classification.md` | active | Claude skill file for NLP |
| Skill: estimate class count | CM | `Ritual_Cover_Management/SKILL-estimate-class-count.md` | active | Claude skill file for class count |
| Project memory | CM | `Ritual_Cover_Management/project_cover_management.md` | legacy | Working memory; content absorbed into this programme |
| Security incident: exposed API keys (2026-06-02) | CM | `Ritual_Cover_Management/SECURITY-INCIDENT-2026-06-02-exposed-keys.md` | **OPEN** | Two credentials were committed to the repository, including a Supabase service key. Rotation status is not confirmed as at 2026-10-18; owner to confirm and record here. |
| Working memory (CLAUDE.md) | CM | `Ritual_Cover_Management/CLAUDE.md` | active | Session working memory; last updated 2026-06-22. Monitor schedule line corrected to hourly on 2026-10-18 |
| Changelogs 2026-06 to 2026-08 (8 files) | CM | `Ritual_Cover_Management/CHANGELOG-2026-06-*.md`, `CHANGELOG-2026-07-03-*.md`, `CHANGELOG-2026-08-11-*.md` | historical | Detail files behind master CHANGELOG entries; keep |
| Plans and TODO (2026-06 to 2026-07) | CM | `PLAN-next-stages-2026-06-21.md`, `PLAN-phase4-offer-matching-2026-06-02-rev.md`, `PLAN-teacher-cover-app-2026-07-09.md`, `TODO-2026-06-22.md` | to confirm | The 06-02 revised plan is historical (shipped). The teacher cover app plan and the TODO list hold open items; owner to confirm what is still planned |

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
| Phase 4 offer matching 2026-06-02 | `MIGRATION-phase4-offer-matching-2026-06-02.sql` | to confirm |
| Momence teacher attributes 2026-06-22 | `MIGRATION-momence-teacher-attrs-2026-06-22.sql` | to confirm |
| ADD: anon-read policy teachers | `migrations/ADD-anon-read-policy-teachers.sql` | **Review before Phase 1** — this policy is being replaced |
| ADD: quoted-reply to whatsapp_messages | `migrations/ADD-quoted-reply-to-whatsapp-messages.sql` | Yes |
| FIX: JSONB string encoding | `migrations/FIX-jsonb-string-encoding-cover-requests.sql` | Yes |
| Phase 2 pre-dedup fixups | `PHASE2-PRE-DEDUP-FIXUPS-2026-05-09.sql` | Yes |
| Phase 2 Mikela merge | `PHASE2-MERGE-MIKELA-2026-05-09.sql` | Yes |

---

## 4. Momence_data

> **Corrected 2026-10-18.** The live Momence code (`Run_Momence_Chain.bat` and the scripts it calls, last changed 2026-08-10) and the current Momence documentation are in the **root of the Momence_data folder** (MFPL OneDrive): `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\`. The copies made in May 2026 under `Ritual_Studio_Ops/services/momence/` are **not** what the scheduled tasks run, and six of their thirteen documents had fallen behind (checked by MD5: ENV_INTEGRATION_SUMMARY, INSTALLATION_SETUP_GUIDE, MOMENCE_SKILL_USAGE_GUIDE, Momence_API_v2_Reference, Momence_data_scraping_wisdom, PIPELINE_MAINTENANCE_GUIDE). Those copies, and the older Dashboard copies, were archived on 2026-10-18. `services/momence/docs/README.md` now points here.

| Document | Owner | Location | Status | Notes |
|---|---|---|---|---|
| Pipeline maintenance guide | Momence_data | `Momence_data/PIPELINE_MAINTENANCE_GUIDE.md` | **active — canonical** | Task names, times (chain 00:21, bookings 01:02, dashboard 03:30 waiting for the chain), 4-hour limit, logs. Last updated 2026-08-07. Supersedes the schedule times quoted in the Dashboard `docs/` daily-workflow files |
| CHANGELOG | Momence_data | `Momence_data/CHANGELOG.md` | **active — canonical** | Momence pipeline change history (last entry 2026-08-07) |
| Scraping wisdom | Momence_data | `Momence_data/Momence_data_scraping_wisdom.md` | **active — canonical** | Updated 2026-06-21 |
| API v2 reference | Momence_data | `Momence_data/Momence_API_v2_Reference.md` | **active — canonical** | Updated 2026-06-21 |
| Cookie auth reference | Momence_data | `Momence_data/Momence_Cookie_Auth_Reference.md` | **active — canonical** | |
| Skill usage guide | Momence_data | `Momence_data/MOMENCE_SKILL_USAGE_GUIDE.md` | **active — canonical** | Updated 2026-07-22 |
| Installation setup guide | Momence_data | `Momence_data/INSTALLATION_SETUP_GUIDE.md` | **active — canonical** | Updated 2026-07-22 |
| Env integration summary | Momence_data | `Momence_data/ENV_INTEGRATION_SUMMARY.md` | **active — canonical** | Updated 2026-07-22 |
| Handover notes | Momence_data | `Momence_data/HANDOVER_NOTES.md` | active | 2026-03-29 |
| Technical details | Momence_data | `Momence_data/TECHNICAL_DETAILS.md` | active | |
| Data cleanup rules | Momence_data | `Momence_data/DATA_CLEANUP_RULES.md` | active | |
| Quick start / Run now / Verification checklist | Momence_data | `Momence_data/QUICK_START.md`, `RUN_NOW.md`, `VERIFICATION_CHECKLIST.md` | active | February 2026 operator notes; still referenced |
| First-run setup and fix summary | Momence_data | `Momence_data/MOMENCE_FIRST_RUN_SETUP.md`, `FIX_SUMMARY.md` | historical | February 2026. Kept in place because QUICK_START, TECHNICAL_DETAILS and VERIFICATION_CHECKLIST link to them |
| Data pipeline overview (March 2026) | Momence_data | `Momence_data/Ritual_Data_Pipeline.md` | historical | Describes the seven-script Selenium chain before the API steps; the maintenance guide is current |
| Leads scraper | Momence_data | `Momence_data/LEADS_SCRAPER.md` | active | |
| Run report 2026-05-12 | Momence_data | `Momence_data/RUN_REPORT_20260512.md` | historical | One-off run report |
| Rose list, leads journal | Momence_data | `Momence_data/Rose list.md`, `momence_leads_journal.md` | to confirm | Working notes |
| Feb 2026 fix notes (7 files) | Momence_data | `Momence_data/_Doc_Archive/2026-10-18/` (COLUMN_NAME_FIXES, DATAFRAME_FIX, DOWNLOAD_BUTTON_FIX, FIXES_APPLIED, LOGIN_FEATURE_SUMMARY, LOGIN_SETUP_GUIDE, TEST_REPORT) | archived 2026-10-18 | Notes on the superseded form-login scraper. Byte-identical copies also archived from the Dashboard folder |
| May 2026 copies (13 files) | RSO | `_Doc_Archive/2026-10-18/Ritual_Studio_Ops/services/momence/docs/` | archived 2026-10-18 | Stale copies; see the note above |
| Dashboard copies (12 files) | Ritual Dashboard | `Ritual Dashboard/_Doc_Archive/2026-10-18/docs/Momence Scrape documentation/` | archived 2026-10-18 | Older copies of the documents above |
| services/momence README | RSO | `Ritual_Studio_Ops/services/momence/README.md` | historical | Describes the planned code move; the move has not taken effect |
| Pointer to current docs | RSO | `Ritual_Studio_Ops/services/momence/docs/README.md` | active | Added 2026-10-18 |

---

## 5. Ritual Dashboard

> Dashboard remains a downstream analytics consumer. It is not rewritten as part of this programme. Its documentation stays where it is; key documents are indexed here, and every other file in its root and `docs/` folder is listed in Appendix B.

| Document | Owner | Location | Status | Notes |
|---|---|---|---|---|
| Project plan v1.3 | Dashboard | `Ritual Dashboard/docs/Ritual_Dashboard_Project_Plan_v1.3.docx` | active (current, best guess) | Named as the current plan in `Ritual Dashboard/README.md`. Latest version present (metadata dated 2026-03-19). |
| Project plan v1.2 | Dashboard | `Ritual Dashboard/docs/Ritual_Dashboard_Project_Plan_v1.2.docx` | superseded | Replaced by v1.3. |
| Project plan v1.1 | Dashboard | `Ritual Dashboard/docs/Ritual_Dashboard_Project_Plan_v1.1.docx` | superseded | Older version. |
| KPI library v1.2 | Dashboard | `Ritual Dashboard/docs/Ritual_KPI_Library_v1.2.docx` | active (current, best guess) | Named as the current KPI library in `Ritual Dashboard/README.md` and `docs/Teacher_Substitution_Build_Prompts.md`. Latest version present. |
| KPI library v1.1 | Dashboard | `Ritual Dashboard/docs/Ritual_KPI_Library_v1.1.docx` | superseded | Replaced by v1.2. Still cited in `Stage9.0_Changelog.md` for the period it covers. |
| KPI library v1.0 | Dashboard | `Ritual Dashboard/docs/Ritual_KPI_Library_v1.0.docx` | superseded | Older version. |
| Dashboard README | Dashboard | `Ritual Dashboard/README.md` | active | Project structure and module layout (C1 to C8, P0 to P5). Last modified 2026-07-23. |
| Dashboard docs README | Dashboard | `Ritual Dashboard/docs/README.md` | active | Daily operations navigation; header says last updated 19 June 2026. |
| Dashboard CHANGELOG | Dashboard | `Ritual Dashboard/CHANGELOG.md` | active | Last modified 2026-10-17. |
| Teacher cost clean-up, task prompt (16 Oct 2026) | Dashboard | `Ritual Dashboard/Task_Prompt_Teacher_Cost_Cleanup_2026-10-16.md` | active | Source instructions for the $0 teacher-cost clean-up. |
| Teacher cost: null sessions (17 Oct 2026) | Dashboard | `Ritual Dashboard/Teacher_Cost_Null_Sessions_2026-10-17.md` | active | 39 null-cost sessions documented (Part B). |
| Teacher cost: Parts C and D (17 Oct 2026) | Dashboard | `Ritual Dashboard/Teacher_Cost_PartC_PartD_2026-10-17.md` | active | Placeholder allowlist and substitute-rate outcome. |
| Momence scraping docs | Dashboard | `Ritual Dashboard/_Doc_Archive/2026-10-18/docs/Momence Scrape documentation/` | archived | Archived 2026-10-18. See section 4 |
| Daily workflow docs | Dashboard | `Ritual Dashboard/docs/DAILY_WORKFLOW_OVERVIEW.md`, `DAILY_PIPELINE_AUTOMATION.md`, `DAILY_EXPORT_CHECKLIST.md`, `QUICK_REFERENCE.md` | active (times stale) | Still describe the 02:00 / 06:00 schedule of June 2026. Live times: `Momence_data/PIPELINE_MAINTENANCE_GUIDE.md` |
| Weekly report guide and template | Dashboard | `Ritual Dashboard/WEEKLY_REPORT_IMPLEMENTATION_GUIDE.md`, `weekly_report_template.md` | active | Monday 08:00 weekly report |
| Weekly reports | Dashboard | `Ritual Dashboard/reports/weekly_report_YYYY-MM-DD_OWNER.md` and `_TECHNICAL.md` | active (output) | 21 Jun – 4 Oct 2026 present on 2026-10-18; no report yet for the weeks ending 11 Oct |
| Weekly recaps | Dashboard | `Ritual Dashboard/reports/weekly/weekly_recap_YYYYMMDD.md` | active (output) | Last on 2026-09-28 |
| Other reports | Dashboard | `Ritual Dashboard/reports/` (monthly strategy May 2026, reconciliation 15–21 Jun, workbook migration audit, c5 teachers draft) | historical | |
| Module specifications | Dashboard | `Ritual Dashboard/specs/` (C1–C10, P0–P5, DATA_CONTRACT, Dashboard_L0/L1) | active | Design-time specs (April–June 2026); README is the current module status |
| Class margin calculation | Dashboard | `Ritual Dashboard/Class_Margin_Calculation.md` | active | Updated 2026-10-17 |
| C1 API migration plan and progress | Dashboard | `Ritual Dashboard/C1_API_Migration_Plan.md`, `C1_API_Migration_Phase1_Progress.md` | active | Remaining work (Structural plan S3) |
| C1 recommended changes (root copy, 6 Mar) | Dashboard | `Ritual Dashboard/_Doc_Archive/2026-10-18/C1 Recommended changes 2026 30 06.md` | archived | Older copy; the 12 Apr version stays in `docs/` |
| Data integrity audit set (April 2026) | Dashboard | `Ritual Dashboard/Data_Integrity_Audit_*.md`, `Findings_Register.md`, `QC_Inspection_2026-04-26.md`, `Post Stage 8*.md`, `Stage*_Changelog.md`, `Stage*_Investigation_*.md`, `Stage6_Owner_Decisions_BA_Review.md`, `Stage 8-5 Changes.md` | historical | The audit trail behind the Work Review (S6, S7). Recommended for a `docs/audits/2026-04/` subfolder (decision needed) |
| Dashboard help page | Dashboard | `Ritual Dashboard/dashboard/help.html` | **missing** | Linked from the dashboard navigation (`assets/components.js`) but the file does not exist |


---

## 6. Reference & Brand

| Document | Owner | Location | Status | Notes |
|---|---|---|---|---|
| Ritual Brand guidelines | Cross-project | `Ritual_Apps/RITUAL_BRAND.md` | active | Brand colours, fonts, voice |
| Xero API integration guide | TM | `Ritual_Teacher_Management/Xero API Integration Architecture and Implementation Guide.docx` | legacy | Not in scope for this programme |
| Firebase schema analysis | CleanSweep | `Ritual_Apps/FIREBASE_SCHEMA_ANALYSIS.md` | historical | CleanSweep migration; see section 11 |
| Firebase-to-Supabase mapping | CleanSweep | `Ritual_Apps/FIREBASE_TO_SUPABASE_MAPPING.md` | historical | CleanSweep migration; see section 11 |
| Cover Management design system | Cross-project | `Ritual_Apps/Ritual Cover Management Design System/` (README, SKILL, ui_kits, source_reference) and `.zip` | active (snapshot) | Packaged design system and skill, 2026-05-10. Its `RITUAL_BRAND.md` is identical to the root copy; `source_reference/` holds May 2026 snapshots of the CM README, ARCHITECTURE, QUICKREF and SCHEMA |
| Task management comparison | Cross-project | `Ritual_Apps/Task_Management_Comparison.md` | historical | Asana versus ClickUp, 2026-06-19 |

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
| Staff Guide (Help modal) | RSO | `Ritual_Studio_Ops/app/ritual-studio-ops-v2.html` (Help modal) | active (**uncommitted**) | Static staff guide replaces the developer-guide fetch, which returned 404 and left the modal on "Loading guide...". The developer prompt guide and the workflow SVG are not published to the app. |
| Security incident, exposed keys | RSO | `Ritual_Cover_Management/SECURITY-INCIDENT-2026-06-02-exposed-keys.md` | **OPEN** | Rotation status unknown as of 2026-10-18; owner to confirm. |
| Momence and RLS security notes | RSO | `Ritual_Studio_Ops/docs/SECURITY-RLS-DISABLED-2026-06-05.md` | to confirm | Not previously indexed. |
| Portal developer notes | RSO | `Ritual_Studio_Ops/docs/PORTAL-DEVELOPER.md` | active | Referenced by the Finance row; not previously indexed. |
| Roadmap | RSO | `Ritual_Studio_Ops/docs/ROADMAP.md` | to confirm | Not previously indexed. |
| Cost tracking design | RSO | `Ritual_Studio_Ops/docs/Cost_Tracking_Design.md` | to confirm | Not previously indexed. |
| Cover auth notes | RSO | `Ritual_Studio_Ops/docs/ritual-cover-management-auth-notes.md` | to confirm | Not previously indexed. |
| Changelog 2026-05-26 (portal campaign tile) | RSO | `Ritual_Studio_Ops/docs/CHANGELOG-2026-05-26-portal-campaign-tile.md` | to confirm | Not previously indexed. |
| Migrations 2026-06-15 (campaigns release 4 and 5; margin columns; sender name) | RSO | `Ritual_Studio_Ops/migrations/2026-06-15-*.sql` (4 files) | to confirm | Not previously indexed. |
| Stray app files | RSO | `Ritual_Studio_Ops/app/v2-relay.html`, `index.html.old`, `index.html.2605` | to confirm | Not documentation, so not archived in the 2026-10-18 pass. `app/` is the deploy folder, so these are published with every deploy — owner to confirm removal |
| Management Portal (LIVE) | RSO | `Ritual_Studio_Ops/app/index.html` | active | Launcher hub for the new system; carries the emblem badge. Adapted from the legacy CM portal 2026-05-24. |
| Finance & Cashflow dashboard | RSO | `Ritual_Studio_Ops/app/finance-cashflow.html` | active | v1 (2026-05-29). Static client-side cashflow dashboard opened from the portal Finance tile. Embeds Xero Stripe-settlement actuals Jul 2025 - Feb 2026; 13-week rolling forecast with editable assumptions. No auth gate yet (see PORTAL-DEVELOPER.md security note). |
| Merged app v1 | RSO | `_Doc_Archive/2026-10-18/RSO_archived_duplicates_2026-05-24/ritual-studio-ops-v1.html` | archived | Superseded by v2; truncated/corrupt. Archived 2026-05-24; the whole `RSO_archived_duplicates_2026-05-24` folder moved under `_Doc_Archive` on 2026-10-18 |
| services/momence README | RSO | `Ritual_Studio_Ops/services/momence/README.md` | historical | Momence code move instructions; the move has not taken effect (section 4) |
| services/cover README | RSO | `Ritual_Studio_Ops/services/cover/README.md` | historical | Cover pipeline move instructions (Phase 3). **The scheduled cover tasks still run from `Ritual_Cover_Management/`** (`run_monitor.bat`), and recent fixes (2026-07-03, 2026-08-11) were made there |
| Test suite Phase 2 | RSO | `Ritual_Studio_Ops/scripts/test_phase2.py` | active | 37 checks — merged shell conventions |
| Test suite Phase 3 | RSO | `Ritual_Studio_Ops/scripts/test_phase3.py` | active | 65 checks — cover pipeline re-point |
| Test suite Phase 4 | RSO | `Ritual_Studio_Ops/scripts/test_phase4.py` | active | 24 checks — write-enable and legacy banners |
| Test suite Phase 5 | RSO | `Ritual_Studio_Ops/scripts/test_phase5.py` | active | 28 checks — reconcile script (merger-programme Phase 5, scheme A — see PHASE-NUMBERING.md) |
| Reconcile script | RSO | `Ritual_Studio_Ops/scripts/reconcile.py` | active | Daily parallel-run health check; run once per day during the merger Phase 5 (scheme A) soak |
| Reconcile reports | RSO | `Ritual_Studio_Ops/scripts/reconcile_reports/` | active | Daily plain-text reports written by reconcile.py |
| Source-of-truth map | RSO | `Ritual_Studio_Ops/docs/SOURCE_OF_TRUTH.md` | active, **one correction** | Which file backs which screen (correct). **Correction 2026-10-18:** its backend table says the `services/cover/` and `services/momence/` copies are the live ones; the scheduled tasks actually run `Ritual_Cover_Management/` and `Momence_data/` |
| Deployment map | RSO | `Ritual_Apps/RSO_DEPLOYMENT_MAP.md` | active | Which repo and branch deploys each app (2026-06-02). Custom `lesss.com.au` domains added since are in the Structural Improvements Plan |
| Per-app change prompts | RSO | `Ritual_Apps/RSO_*_Change_Prompt.md` (Campaigns, CoverDashboard, Portal_Login, RitualDashboard, StudioTimetable, TeacherManagement) | active | Read before changing that app. Staging copies (identical) archived from `_claude_stage/` on 2026-10-18 |
| Help modal staff guide | RSO | `Ritual_Studio_Ops/app/ritual-studio-ops-v2.html` (Help & Resources) | active | Built-in staff guide; the fuller version is User Guide 03 |
| Navigation map | RSO | `Ritual_Studio_Ops/docs/NAVIGATION.md` | active | Diagram of how portals, dashboards and external platforms link, plus the Phase 6 Pages consolidation plan. |
| Setup audit (2026-05-24) | RSO | `Ritual_Studio_Ops/docs/AUDIT-RSO-2026-05-24.md` | active | Latest setup audit with severity-rated findings. |
| Migration 2026-05-22: source on cover_requests | RSO | `Ritual_Studio_Ops/migrations/2026-05-22-add-source-to-cover-requests.sql` | active | Adds the `source` column distinguishing whatsapp vs manual cover requests. |
| Migration 2026-05-27: teacher_absences | RSO | `Ritual_Studio_Ops/migrations/2026-05-27-teacher-absences.sql` | active | Creates `teacher_absences` table, trigger, 3 partial indexes, 5 RLS policies. Applied 2026-05-27 via Supabase MCP. |
| Edge Function: parse-cover-request | RSO | Supabase project rfjygyqijwgkmxboddup (deployed via MCP) | active | Called by the v2 Manual Cover Request modal. JWT-verified. No local source file in the repo. |
| Migration 2026-05-22: reference tables | RSO | `G:\Shared drives\RITUAL MASTER DRIVE\Claude Project 20260322\Ritual Studios\migrations\2026-05-22-reference-tables.sql` | applied | Creates membership_types, class_group_mappings; adds teachers.hourly_cost. Applied 2026-05-22. Path not verifiable from the workspace (G: drive not connected). |
| Migration 2026-05-23: locations, rooms, pay rates | RSO | `G:\Shared drives\RITUAL MASTER DRIVE\Claude Project 20260322\Ritual Studios\migrations\2026-05-23-locations-rooms-pay-rates.sql` | applied | Creates locations, rooms, location_aliases, teacher_pay_rate_tiers; adds teachers.default_pay_rate. Applied 2026-05-23. Path not verifiable from the workspace (G: drive not connected). |
| Migration 2026-05-23b: drop check constraints | RSO | `G:\Shared drives\RITUAL MASTER DRIVE\Claude Project 20260322\Ritual Studios\migrations\2026-05-23b-drop-ref-check-constraints.sql` | applied | Drops over-restrictive CHECK constraints on membership_types.membership_type and class_group_mappings.class_group. Applied 2026-05-23. Path not verifiable from the workspace (G: drive not connected). |
| Reference data migration summary | RSO | `G:\Shared drives\RITUAL MASTER DRIVE\Claude Project 20260322\Ritual Studios\migrations\MIGRATION_SUMMARY.md` | active | Full reference for all reference-data tables, migration run order, seed script usage, classify.py behaviour, location alias model, and outstanding items. Last updated 2026-05-23. Owner decision (2026-10-17): classify.py is dead, but this summary still describes it and needs correcting. Path not verifiable from the workspace. |
| Seed script: reference tables | RSO | `G:\Shared drives\RITUAL MASTER DRIVE\Claude Project 20260322\Ritual Studios\scripts\seed_reference_tables.py` | active | Idempotent seed for all 8 reference data sections. Supports --dry-run and --only TABLE flags. Requires SUPABASE_SERVICE_KEY env var (set per session only; do not hardcode). Path not verifiable from the workspace (G: drive not connected). |

**Tables-and-owners matrix** (updated each migration — 2026-05-merged-v1.sql)

| Table | Created by | Phase | Owner | Notes |
|---|---|---|---|---|
| `teachers` | TM original | Pre-merger | TM (RSO from Phase 2) | 262 rows (live count 2026-10-18). RLS on. |
| `class_history` | TM original | Pre-merger | TM | 7,648 rows (live count 2026-10-18). RLS on. |
| `user_profiles` | TM original | Pre-merger | TM | 15 rows (live count 2026-10-18). RLS on. |
| `audit_log` | TM original | Pre-merger | TM | 59 rows (live count 2026-10-18). RLS on. |
| `permissions` | CM migration 2026-05-09 | Pre-merger | TM/CM shared | 26 rows. RLS on. |
| `role_permissions` | CM migration 2026-05-09 | Pre-merger | TM/CM shared | 22 rows. RLS on. |
| `training_courses` | TM (momence_courses_sync.py) | Pre-merger | TM | 10 rows (live count 2026-10-18). RLS off — review. |
| `trainee_enrollments` | TM | Pre-merger | TM | 38 rows (live count 2026-10-18). RLS off — review. |
| `timeslots` | TM | Pre-merger | TM | 13 rows (live count 2026-10-18). RLS off — review. |
| `trainee_bookings` | TM changelog 2026-04-05 | Pre-merger | TM | 15 rows (live count 2026-10-18). RLS off — review. |
| `cover_requests` | CM stage 1 | Pre-merger | CM | 236 rows (live count 2026-10-18). RLS off — review. |
| `cover_candidates` | CM | Pre-merger | CM | 66 rows (live count 2026-10-18). RLS off — review. |
| `cover_notifications` | CM | Pre-merger | CM | 0 rows (live count 2026-10-18). RLS off — review. |
| `whatsapp_channels` | CM stage 1 | Pre-merger | CM | 5 rows (live count 2026-10-18). RLS off — review. |
| `whatsapp_messages` | CM | Pre-merger | CM | 859 rows (live count 2026-10-18). RLS off — review. |
| `whatsapp_monitor_runs` | CM | Pre-merger | CM | 2,905 rows (live count 2026-10-18). RLS off — review. |
| `system_config` | CM stage 1 | Pre-merger | CM | 9 rows (live count 2026-10-18). RLS off — review. |
| `discipline_mappings` | CM | Pre-merger | CM | 6 rows. Superseded by `disciplines`. Kept for backwards compat. |
| `disciplines` | RSO | Phase 1 (2026-05-21) | RSO | Canonical taxonomy. 5 rows seeded. RLS on. |
| `studios` | RSO | Phase 1 (2026-05-21) | RSO | Canonical studios. Seed: Palm Beach (active), Robina (active), Mermaid (`is_active = false`, closed/retired). RLS on. |
| `momence_sessions` | CM (MIGRATION-momence-sessions-table-2026-05-11) | Pre-merger — **already populated** | RSO | 10,932 rows (live count 2026-10-18). RLS on. Phase 7 session sync is already running. |
| `momence_members` | RSO | Phase 1 (2026-05-21) — empty placeholder | RSO | 0 rows. Filled in Phase 7. RLS on. |
| `momence_bookings` | RSO | Phase 1 (2026-05-21) — empty placeholder | RSO | 0 rows. Filled in Phase 7. RLS on. |
| `momence_sync_runs` | RSO | Phase 1 (2026-05-21) | RSO | Audit log for Phase 7 sync jobs. RLS on. |
| `teacher_absences` | TM | 2026-05-27 (migration 2026-05-26-teacher-absences.sql) | TM | 58 rows (live count 2026-10-18). RLS on (5 policies). Soft-delete via `deleted_at`. |
| `membership_types` | external workstream (Data workbook, 2026-05-22) | Pre-existing | RSO (Settings → Reference Data) | 187 rows. RLS on. Comment references the Data workbook for Ritual analysis. Owner documented 2026-10-18. |
| `class_group_mappings` | external workstream (Data workbook, 2026-05-22) | Pre-existing | RSO (Settings → Reference Data) | 87 rows. RLS on. Class-name to coarse-group mapping. Owner documented 2026-10-18. |
| `locations` | external workstream | Pre-existing | Unassigned | 3 rows. RLS on. Overlaps conceptually with `studios` - taxonomy reconciliation pending. |
| `rooms` | external workstream | Pre-existing | Unassigned | 5 rows. RLS on. |
| `location_aliases` | external workstream | Pre-existing | Unassigned | 8 rows. RLS on. |
| `teacher_pay_rate_tiers` | external workstream | Pre-existing | Unassigned | 8 rows. RLS on. |

---

## 8. Programme, strategy and security (`Ritual_Apps/Docs/`)

`Docs/` is the canonical folder for programme deliverables (set by Mark on 2026-06-16). Its own contents list is `Docs/README.md`.

| Document | Location | Status | Notes |
|---|---|---|---|
| Docs folder README | `Docs/README.md` | active | Contents list; rewritten 2026-10-18 |
| Work review, 14 Oct 2026 | `Docs/Ritual_Work_Review_2026-10-14.md` | active | Work to date against the owners' four objectives (sources S1–S27). Working copy on claude.ai |
| Phase 2 proposal, 14 Oct 2026 | `Docs/Ritual_Phase2_Proposal_2026-10-14.md` | active | 13-week proposal: measure, move, hand over |
| Meeting pack index, 14 Oct 2026 | `Docs/Ritual_Meeting_Pack_2026-10-14_INDEX.md` | active | Links to the four meeting items and the points to settle |
| Improvement Plan v3 | `Docs/Ritual_Studios_Improvement_Plan_v3_Structural_Operational_Functional.md` | active | 20 initiatives across structural, operational and functional lenses (29 Jun 2026). Supersedes the framing of v2 |
| Improvement Plan v2 | `Docs/Ritual_Studios_Improvement_Plan_v2.docx` | superseded | 16 Jun 2026. Kept: holds the runner-laptop workstream (its section 6) in full — owner to confirm whether to archive |
| Structural Improvements Completion Plan | `Docs/Ritual_Studios_Structural_Improvements_Completion_Plan.md` | active | Access unification (A1–A9), S3–S6 (29 Jul 2026) |
| Application Security Standard v1.0 | `Docs/Ritual_Studios_Application_Security_Standard.md` | active | The standard access pattern for every Ritual app (29 Jul 2026) |
| SSO bridge spike and rollout | `Docs/A3_sso_bridge/README.md`, `ROLLOUT_PLAYBOOK.md` (+ `bridge.js`, `bridge_test.html`) | active | Cover done; Dashboard not needed; Ops and Campaigns pending (3 Aug 2026) |
| Automation opportunities register | `Docs/Ritual_Automation_Opportunities_From_Drive_2026-06-29.md` | active | The register of 19 candidates |
| Automation detailed plan | `Docs/Ritual_Automation_Opportunities_Detailed_Plan_2026-07-02.md` | active | Companion to the register; approval not recorded |
| Automation board deck | `Docs/Ritual_Automation_Suite_Board_Deck.pptx` | active | Running cost about $125–$160 a month |
| Phase 0 plan | `Docs/Ritual_Studios_Phase0_Plan.md` and `.docx` | historical | Phase 0 security runbook (16 Jun 2026). Exit gate met 30 Jun 2026 |
| Phase 0 remaining steps | `Docs/Ritual_Studios_Phase0_Remaining_Steps.md` | historical | 18 Jun 2026 working list; cited by v3 and the completion plan |
| Phase 0 completion plan | `Docs/Ritual_Studios_Phase0_Completion_Plan.md` | historical | Record of Phase 0 completion (1 Jul 2026) |
| Phase 0 preparation | `Docs/Phase0_prep/` (C1_and_P0-3_plan, HANDOVER_when_you_return, REDIRECT_DEPLOY, TEST_REGIME_ops_login_and_reconcile, SQL and JS templates) | historical | June–July 2026 |
| Portability recommendations | `Docs/Portability_Recommendations.md` | to confirm | Multi-studio deployment ideas (1 Jul 2026) |
| Folder reorganisation plan v1.1 | `Docs/Ritual_Folder_Reorganisation_Plan_v1.1.docx` | to confirm | Not known whether executed |
| Folder reorganisation plan v1 | `Docs/Ritual_Folder_Reorganisation_Plan.docx` | superseded | By v1.1 |
| Templates | `Docs/Long_Tail_Operations_System_Template.docx`, `Docs/Studio_Diagnostic_Intake_Questionnaire.docx` | to confirm | Consultancy templates |
| Supporting files | `Docs/*.csv`, `Docs/*.xlsx`, `Docs/*.ps1`, `Docs/ritual-pre-commit-hook.sh` | — | Data extracts and scripts, not documentation |
| Documentation audit | `Docs/Documentation_Audit_2026-10-18.md` | active | This pass |

---

## 9. User guides and video prompts (`Ritual_Apps/Docs/User_Guides/`)

Written 2026-10-18 for staff, teachers and owners, from the live screen labels. Diagrams are Mermaid; screen illustrations are SVG in `User_Guides/images/`.

| Guide | Location | Audience |
|---|---|---|
| Guide index | `Docs/User_Guides/README.md` | Everyone |
| 01 Start here: signing in and roles | `Docs/User_Guides/01_Start_Here_Signing_In_and_Roles.md` | Everyone |
| 02 Management Portal | `Docs/User_Guides/02_Management_Portal.md` | All staff; administrators |
| 03 Studio Ops: Teachers | `Docs/User_Guides/03_Studio_Ops_Teachers.md` | Coordinators, administrators |
| 04 Cover Management | `Docs/User_Guides/04_Cover_Management.md` | Coordinators (replaces the June 2026 training guide) |
| 05 Studio Timetable | `Docs/User_Guides/05_Studio_Timetable.md` | All staff |
| 06 For teachers | `Docs/User_Guides/06_For_Teachers.md` | Teachers, applicants |
| 07 Campaign Planning | `Docs/User_Guides/07_Campaign_Planning.md` | Campaign team |
| 08 Analytics Dashboard and weekly reports | `Docs/User_Guides/08_Analytics_Dashboard_and_Weekly_Reports.md` | Owners, management |
| 09 Finance and Cashflow | `Docs/User_Guides/09_Finance_and_Cashflow.md` | Owners |
| 10 CleanSweep (not yet live) | `Docs/User_Guides/10_CleanSweep.md` | Cleaning team |
| 11 Behind the scenes: daily automation | `Docs/User_Guides/11_Behind_the_Scenes_Daily_Automation.md` | Administrator |
| 12 Troubleshooting and FAQ | `Docs/User_Guides/12_Troubleshooting_and_FAQ.md` | Everyone |
| 13 Glossary | `Docs/User_Guides/13_Glossary.md` | Everyone |
| Video series prompts (V01–V12) | `Docs/User_Guides/Video_Series_Prompts.md` | Video producers |
| Illustrations | `Docs/User_Guides/images/` (portal, cover dashboard, Studio Ops, timetable, colour keys, KPI tile) | — |

---

## 10. Campaign Planning (`Ritual_Apps/Ritual marketing/`)

App: `Ritual marketing/campaign-planning.html` (`v5.2.1 R5`), deployed to `ritual-campaign-planning.pages.dev` from `Mark-Fellows/ritual-campaign-planning` (`main`). Not previously indexed.

| Document | Location | Status | Notes |
|---|---|---|---|
| Build stages (release plan) | `Ritual marketing/Docs/Campaign Planning tool build stages.md` | **active — authoritative** | Releases 1–5.2 done; Release 6 next |
| Setup guide | `Ritual marketing/Docs/campaign-planning-README.md` | active (dated) | Written for Release 3; roles, migrations, digest. Current release is 5.2.1 |
| Process design review | `Ritual marketing/Docs/Campaign Planning tool process design review.md` | active | Reasoning behind the release plan |
| Build summaries v1, v2, v3, v4, v5, v5.1, v5.2 | `Ritual marketing/Docs/Campaign Planning tool build v*.md` | historical | One per release |
| Release 4 and 5.2 implementation plans | `Ritual marketing/Docs/Release 4 implementation plan.md`, `Release 5.2 implementation plan.md` | historical | |
| Progress logs | `Ritual marketing/Docs/release-4-progress-log.md`, `release-5-progress-log.md`, `release-5-2-progress-log.md`, `campaign-planning-hygiene-progress.md` | historical | |
| Hygiene prompt | `Ritual marketing/Docs/RSO_Campaigns_Hygiene_Prompt.md` | historical | Release 5.1 |
| Brand voice (campaign) | `Ritual marketing/Docs/files/01_brand_voice.md` | superseded | Moved into `system_config.campaign_brand_voice` in Release 5.2 |
| First Cowork prompt; future tasks checklist | `Ritual marketing/Docs/files/03_cowork_first_prompt.md`, `04_future_tasks_checklist.md` | historical | Release sequencing superseded by the build stages document |
| SQL migrations 02–06 | `Ritual marketing/Docs/0[2-6]_campaign_planning_*.sql` | applied | Releases 1–5 |
| Digest Edge Function source | `Ritual marketing/Docs/campaign-digest-edge-function.ts` | active | Monday and Thursday digest |
| Change prompt | `Ritual_Apps/RSO_Campaigns_Change_Prompt.md` | active | |

---

## 11. CleanSweep (cleaning-team app)

Code is in the `Ritual_Apps` root (Next.js: `src/`, `package.json`); the parent `Ritual_Apps` git repository is this app (the deployment map calls it "an old Firebase/Next.js scaffold"). Migration from Firebase to Supabase is code-complete (9 Sep 2026); testing and deployment pending. Not previously indexed.

| Document | Location | Status | Notes |
|---|---|---|---|
| Migration plan | `MIGRATION_PLAN.md` | active | Firebase to Supabase, phased |
| Firebase schema analysis; Firebase-to-Supabase mapping | `FIREBASE_SCHEMA_ANALYSIS.md`, `FIREBASE_TO_SUPABASE_MAPPING.md` | historical | Phase 1 |
| Schema implementation guide and SQL | `SUPABASE_SCHEMA_IMPLEMENTATION.md`, `SUPABASE_SCHEMA_DESIGN.sql` | active | Phase 2 |
| Phase 3a/3b/3c guides | `PHASE_3A_AUTH_MIGRATION.md`, `PHASE_3A_SETUP_GUIDE.md`, `PHASE_3B_DATA_MIGRATION.md`, `PHASE_3B_SETUP_GUIDE.md`, `PHASE_3C_SUPABASE_SERVICE_LAYER.md`, `PHASE_3C_SETUP_GUIDE.md` | historical | Completed |
| Phase 3 completion | `PHASE_3_COMPLETION.md` | active | Status as at 9 Sep 2026 |
| Phase 4 testing and deployment | `Claude outputs/PHASE_4_SUMMARY.md`, `PHASE_4_IMPLEMENTATION_GUIDE.md`, `PHASE_4_TESTING_DEPLOYMENT.md`; `TESTING_CHECKLIST.md` | active | Next step |
| Phase 2 import guide | `Claude outputs/PHASE-2-IMPORT-GUIDE.md` | historical | |
| Original project export | `Ritual_CleanSweep/Docs/MASTER_DOCS.md`, `MASTER_SOURCE.md`, `MASTER_DATA.json`, `config.ts` | historical | Firebase Studio export used as the migration source |
| User guide | `Docs/User_Guides/10_CleanSweep.md` | active | Placeholder until release |

---

## 12. Other documents in the `Ritual_Apps` root

| Document | Location | Status | Notes |
|---|---|---|---|
| Reference data migration summary (copy) | `MIGRATION_SUMMARY.md` | active, **one correction** | Copy of the G-drive summary (reference tables, seed script). Owner decision 2026-10-17: `classify.py` is dead, but this summary still describes it. Not a CleanSweep document despite the name |
| Brand guide | `RITUAL_BRAND.md` | active | Section 6 |
| Deployment map; change prompts | `RSO_DEPLOYMENT_MAP.md`, `RSO_*_Change_Prompt.md` | active | Section 7 |
| Task management comparison | `Task_Management_Comparison.md` | historical | Section 6 |
| Working text files | `Class Cancellation.txt`, `The Method Three Required Elements.txt`, `audit_out.txt`, `git*_out.txt`, `rso_git_result.txt` | — | Notes and command output, not documentation. Candidates for a tidy-up (decision needed) |

---

## 13. Archive

Superseded and duplicate documentation is kept, not deleted, under a `_Doc_Archive` folder at the root of each top-level folder. Files keep their original relative path beneath a dated folder, so restoring is a move back. Each archive has an `ARCHIVE_MANIFEST.md` listing every item and the reason.

| Archive | Manifest | Items archived 2026-10-18 |
|---|---|---|
| `Ritual_Apps/_Doc_Archive/` | `Ritual_Apps/_Doc_Archive/ARCHIVE_MANIFEST.md` | 13: `_claude_stage/` (6 identical copies), `RSO_archived_duplicates_2026-05-24/` (earlier archive, moved out of the main folder), TM merger plans v1 and v2 copy, TM investigation copy, merger prompt, "Recommendations re id", `Ritual_Studio_Ops-Legacy/` stubs, CM session log, CM June training guide, `services/momence/docs/` (13 stale copies), two empty folders created in error |
| `Ritual Dashboard/_Doc_Archive/` | `Ritual Dashboard/_Doc_Archive/ARCHIVE_MANIFEST.md` | 4: `docs/Momence Scrape documentation/` (12), `docs/archive/` (7 Feb 2026 fix notes), root copy of "C1 Recommended changes", an empty text file |
| `Momence_data/_Doc_Archive/` | `Momence_data/_Doc_Archive/ARCHIVE_MANIFEST.md` | 7 Feb 2026 fix notes for the old form-login scraper |

Earlier archive folders that remain in place and are **not** documentation: `Ritual Dashboard/_to_delete/`, `Ritual Dashboard/backups/`, `Momence_data/Archive/` (the nightly data archive — do not confuse with `_Doc_Archive`), `Momence_data/_backups_20260811/`, `Ritual_Cover_Management/backups/`, `Ritual_Studio_Ops/backups/`.

---

## Appendix A: Cover Management files not individually reviewed

71 `.md`/`.txt` files in `Ritual_Cover_Management/` (root only). Statuses assigned on 2026-10-18 from each file's title, date, cross-references and (for Markdown) its content. "Working output" files are command or diagnostic output, not documentation; they are left in place because scripts may write to them.

| File | Last modified | Status |
|---|---|---|
| `ARCHITECTURE.md` | 2026-04-21 | active — developer reference (2026-04-21; check against SCHEMA.md for later tables) |
| `backfill_fn.txt` | 2026-04-23 | working output — not documentation |
| `Changelog WhatsApp.md` | 2026-04-13 | historical |
| `CHANGELOG-2026-04-13-nlp-sender-fallback.md` | 2026-04-13 | historical (in master CHANGELOG) |
| `CHANGELOG-2026-04-23-avail-slots.md` | 2026-04-23 | historical (in master CHANGELOG) |
| `CHANGELOG-2026-05-07-scheduled-task-setup.md` | 2026-05-07 | historical (in master CHANGELOG) |
| `CHANGELOG-2026-05-08-phase1-and-resilience.md` | 2026-05-08 | historical (in master CHANGELOG) |
| `CHANGELOG-2026-05-09.md` | 2026-05-09 | historical (in master CHANGELOG) |
| `CHANGELOG-2026-05-11-momence-sessions-table.md` | 2026-05-11 | historical (in master CHANGELOG) |
| `CHANGELOG-2026-05-16.md` | 2026-05-16 | historical (in master CHANGELOG) |
| `CHANGELOG-2026-05-17.md` | 2026-05-16 | historical (in master CHANGELOG) |
| `CHANGELOG-2026-06-01-whatsapp-export.md` | 2026-06-01 | historical |
| `CHANGELOG-2026-06-02-edge-changeover-and-resilience.md` | 2026-06-02 | historical |
| `CHANGELOG-2026-06-02-phase4-offer-matching.md` | 2026-06-02 | historical |
| `CHANGELOG-2026-06-09-backfill-button.md` | 2026-06-09 | historical |
| `CHANGELOG-2026-06-15-dedup-fix-api-keys-waReplyMap.md` | 2026-06-15 | historical |
| `CHANGELOG-2026-06-15-timetable-v2-margin-columns.md` | 2026-06-15 | historical |
| `CHANGELOG-2026-07-03-browser-drivability-and-daily-refresh.md` | 2026-07-04 | historical (detail behind master CHANGELOG) |
| `CHANGELOG-2026-08-11-whatsapp-logout-and-session-restore-wipe.md` | 2026-08-11 | historical (detail behind master CHANGELOG) |
| `CHANGELOG-dashboard-spinning-fix-20260520.md` | 2026-05-20 | historical (in master CHANGELOG) |
| `CLAUDE.md` | 2026-06-22 | active (schedule line corrected 2026-10-18) |
| `Cover management stages brief description.txt` | 2026-04-13 | historical |
| `cp_run_output.txt` | 2026-06-09 | working output — not documentation |
| `DEPLOY.md` | 2026-05-07 | active — check against RSO_DEPLOYMENT_MAP.md |
| `DEVELOPER.md` | 2026-06-15 | active — developer onboarding |
| `diag_atlogon_trigger.txt` | 2026-05-08 | working output — not documentation |
| `diag_chat_dump.txt` | 2026-06-09 | working output — not documentation |
| `diag_run_log.txt` | 2026-05-07 | working output — not documentation |
| `diag_scheduled_tasks.txt` | 2026-05-07 | working output — not documentation |
| `diag_shaye_records.txt` | 2026-05-07 | working output — not documentation |
| `diag_teachers_dump.txt` | 2026-06-09 | working output — not documentation |
| `HANDOFF-coverage-type-execution.md` | 2026-04-20 | historical (April 2026 handoff) |
| `HANDOFF-START-HERE.md` | 2026-04-20 | historical (April 2026 handoff; start with README.md and DEVELOPER.md instead) |
| `HELP.md` | 2026-05-08 | active (schedule corrected 2026-10-18) |
| `Index.md` | 2026-05-16 | superseded by this index |
| `INVESTIGATION-teachers-dropdown-2026-05-14.md` | 2026-05-21 | historical (canonical copy) |
| `Nested_Messages.md` | 2026-05-19 | active |
| `page_structure.txt` | 2026-04-13 | working output — not documentation |
| `PHASE-2-DEDUP-DESIGN.md` | 2026-05-08 | historical (shipped) |
| `PHASE-3-DASHBOARD-DESIGN.md` | 2026-05-08 | historical (shipped) |
| `PHASE-4-OFFER-MATCHING-DESIGN.md` | 2026-06-21 | historical (shipped 2026-06-02) |
| `PHASE-5-USER-ADMIN-DESIGN.md` | 2026-06-02 | superseded by USER-ADMIN-BUILD-SPEC.md |
| `PHASES-quick-invoke.md` | 2026-04-20 | historical |
| `PLAN-coverage-type-feature.md` | 2026-04-20 | historical (signed off 2026-04-21) |
| `PLAN-next-stages-2026-06-21.md` | 2026-06-21 | historical (folded into Improvement Plan v3) |
| `PLAN-phase4-offer-matching-2026-05-16.md` | 2026-06-02 | historical (shipped) |
| `PLAN-phase4-offer-matching-2026-06-02-rev.md` | 2026-06-02 | historical (shipped) |
| `PLAN-teacher-cover-app-2026-07-09.md` | 2026-07-11 | to confirm — open plan |
| `post_reboot_check.txt` | 2026-05-08 | working output — not documentation |
| `probe_chrome.txt` | 2026-05-07 | working output — not documentation |
| `probe_chrome_tabs.txt` | 2026-05-07 | working output — not documentation |
| `project_cover_management.md` | 2026-05-08 | legacy (still linked from HELP.md) |
| `q_out.txt` | 2026-04-23 | working output — not documentation |
| `QUICKREF.md` | 2026-06-16 | active |
| `README.md` | 2026-07-17 | active |
| `requirements.txt` | 2026-04-20 | code (Python dependencies) |
| `SCHEMA.md` | 2026-06-21 | active |
| `SECURITY-INCIDENT-2026-06-02-exposed-keys.md` | 2026-06-16 | **OPEN** — rotation not confirmed |
| `SESSION-LOG-2026-05-08-evening.md` | 2026-05-08 | archived 2026-10-18 |
| `SETUP.md` | 2026-06-16 | active |
| `setup_browser_refresh_task.txt` | 2026-07-03 | working output — not documentation |
| `setup_scheduled_tasks.txt` | 2026-05-28 | working output — not documentation |
| `SIGNOFF-coverage-type-2026-04-21.md` | 2026-04-21 | historical |
| `SKILL-coverage-type-classification.md` | 2026-04-21 | active |
| `SKILL-estimate-class-count.md` | 2026-04-13 | active |
| `stage3_API_TEST_REPORT.txt` | 2026-04-14 | historical test output |
| `stage3_live_test_output.txt` | 2026-04-14 | historical test output |
| `TODO-2026-06-22.md` | 2026-06-29 | to confirm — open items |
| `trigger_monitor_run.txt` | 2026-07-03 | working output — not documentation |
| `TROUBLESHOOTING.md` | 2026-06-02 | active |
| `WORKFLOW-SUMMARY.md` | 2026-04-20 | historical (before offer matching) |

---

## Appendix B: Ritual Dashboard files not individually reviewed

Root `.md` files: 44. Files in `docs/` (top level): 42. The Momence scrape subfolder is covered in section 4. Statuses assigned on 2026-10-18 from each file's title, date and cross-references; Word and PDF files were not opened. Rows after `Xero Backfill…` are in `docs/`.

| File | Last modified | Status |
|---|---|---|
| `A2_ClassID_SessionID_Analysis.md` | 2026-04-26 | historical analysis |
| `C1 Recommended changes 2026 30 06.md` | 2026-03-06 | archived 2026-10-18 (root copy, 2026-03-06) |
| `C1_API_Migration_Phase1_Progress.md` | 2026-05-03 | active (remaining work: Structural plan S3) |
| `C1_API_Migration_Plan.md` | 2026-05-03 | active (remaining work: Structural plan S3) |
| `Changelog - 2026-04-17.md` | 2026-05-05 | historical (v4.1.0 bookings fixes; not repeated in CHANGELOG.md, so keep) |
| `Class_Margin_Calculation.md` | 2026-10-17 | active |
| `COMPETITIVE_GAPS_EXECUTIVE_SUMMARY.md` | 2026-07-16 | reference (Jul 2026) |
| `COMPETITIVE_INTELLIGENCE_ANALYSIS.md` | 2026-07-16 | reference (Jul 2026) |
| `Course_Revenue_Recommended_Actions.md` | 2026-08-05 | active — open issue (course revenue restatement) |
| `Course_Session_Revenue_Investigation_2026-08-05.md` | 2026-08-05 | active — open issue (course revenue restatement) |
| `Data_Integrity_Audit_2026-04-17.md` | 2026-04-18 | historical audit record |
| `Data_Integrity_Audit_Index.md` | 2026-04-26 | historical audit record (index of the audit set) |
| `Data_Integrity_Audit_Stage1.md` | 2026-04-18 | historical audit record |
| `Data_Integrity_Audit_Stage2.md` | 2026-04-18 | historical audit record |
| `Data_Integrity_Audit_Stages3-6.md` | 2026-04-22 | historical audit record |
| `Findings_Register.md` | 2026-04-26 | historical audit record (334 findings) |
| `Memberships_Dashboard_Investigation_2026-05-01.md` | 2026-05-03 | historical |
| `Momence_API_Call_Reference.md` | 2026-05-03 | reference (May 2026; see Momence_data/Momence_API_v2_Reference.md) |
| `momence_booking_id_test.md` | 2026-04-26 | historical |
| `Post Stage 8 Integrity Audit.md` | 2026-04-26 | historical audit record |
| `Post Stage 8.9 Close-Out Audit.md` | 2026-04-27 | historical audit record (M4, M5 left open) |
| `QC_Inspection_2026-04-26.md` | 2026-04-26 | historical audit record |
| `Reconciliation_20260323.md` | 2026-03-23 | historical |
| `SCHEDULING_ENGINE_QUICK_START.md` | 2026-07-16 | reference (Jul 2026) |
| `SCHEDULING_OPTIMISATION_FRAMEWORK.md` | 2026-07-16 | reference (Jul 2026) |
| `Setup_Summary.md` | 2026-04-02 | historical (GitHub Desktop workflow, replaced by auto-commit on 2026-06-19) |
| `Stage 8-5 Changes.md` | 2026-04-26 | historical audit record |
| `Stage6_Owner_Decisions_BA_Review.md` | 2026-04-26 | historical audit record |
| `Stage7_Changelog.md` | 2026-04-26 | historical audit record |
| `Stage8.1_Changelog.md` | 2026-04-26 | historical audit record |
| `Stage8.4_Changelog.md` | 2026-04-26 | historical audit record |
| `Stage8.5_Changelog.md` | 2026-04-26 | historical audit record |
| `Stage8.5_Investigation_fp_unmatched.md` | 2026-04-26 | historical audit record |
| `Stage8.6_Changelog.md` | 2026-04-26 | historical audit record |
| `Stage8.7_Changelog.md` | 2026-04-26 | historical audit record |
| `Stage8.8_Investigation_stale_collectors.md` | 2026-04-27 | historical audit record |
| `Stage8.9_Changelog.md` | 2026-04-27 | historical audit record |
| `Stage9.0_Changelog.md` | 2026-05-03 | historical audit record |
| `WEEKLY_RECOMMENDATION_TRACKER.md` | 2026-07-16 | to confirm — last updated 2026-07-16 |
| `WEEKLY_REPORT_IMPLEMENTATION_GUIDE.md` | 2026-06-19 | active |
| `WEEKLY_REPORT_SAMPLE.md` | 2026-06-21 | superseded by real reports (kept: linked from the implementation guide) |
| `WEEKLY_REPORT_SAMPLE_UPDATED.md` | 2026-06-21 | superseded by real reports |
| `weekly_report_template.md` | 2026-06-26 | active |
| `Xero Backfill & Financial Model Update — Session Summary.md` | 2026-05-29 | historical |
| `12-12 Meeting- Defining Mark's Role and Operational Strategy.docx` | 2025-12-12 | reference — source of owner objectives (S3) |
| `12-12 Meeting- Defining Mark's Role and Operational Strategy.pdf` | 2025-12-12 | reference — PDF of the above |
| `C1 Recommended changes 2026 30 06.md` | 2026-04-12 | historical (current copy, in docs/) |
| `CGPT ideas for campaign maangement Jan 2026.docx` | 2026-01-06 | historical |
| `Class change suggestions wc 12Jan26.docx` | 2026-01-13 | historical |
| `Cloudflare_GitHub_Deployment_Guide.md` | 2026-04-12 | historical (April 2026; see RSO_DEPLOYMENT_MAP.md) |
| `DAILY_EXPORT_CHECKLIST.md` | 2026-06-20 | active (times stale; see section 5) |
| `DAILY_PIPELINE_AUTOMATION.md` | 2026-06-19 | active (times stale; see section 5) |
| `DAILY_WORKFLOW_OVERVIEW.md` | 2026-06-19 | active (times stale; see section 5) |
| `Dashboard_Data_Fixes_2026-04-12.md` | 2026-04-12 | historical |
| `Draft Quarterly Agenda for Ritual v1.docx` | 2026-01-08 | reference — source of owner goals (S1) |
| `KPI_Drilldown_Design_v1.0.md` | 2026-06-15 | active (design) |
| `manual and automatic processes, procedures, and work instructions for the studio.docx` | 2026-02-09 | reference |
| `Meeting notes 26 01 19.docx` | 2026-01-19 | historical |
| `Meeting notes 27 01 19.docx` | 2026-01-27 | historical |
| `Meeting notes February 4th 2026.docx` | 2026-02-04 | historical |
| `Membership_Attendance_Report_Documentation.docx` | 2026-03-31 | reference |
| `Mermaid lease.docx` | 2026-01-08 | historical (studio closed January 2026) |
| `Minutes of 4 February 2026.docx` | 2026-02-12 | historical |
| `Notes on Cash improvement.docx` | 2026-03-25 | historical |
| `Notes on Cash improvement.txt` | 2026-03-25 | historical (text copy of the above) |
| `Proposal 14 November 2025.docx` | 2025-11-14 | historical |
| `Proposal 20 November 2025.docx` | 2025-11-26 | reference — original scope (S4) |
| `QUICK_REFERENCE.md` | 2026-06-19 | active (times stale; see section 5) |
| `Ritual notes and clippings.docx` | 2025-11-15 | historical |
| `Ritual notes.docx` | 2025-11-14 | historical |
| `Ritual Studio -  A Strategic Framework for Operational Excellence.docx` | 2025-12-17 | historical |
| `RITUAL STUDIO --  ASANA ARCHITECTURE FOR OPERATIONAL TURNAROUND.docx` | 2025-12-18 | historical |
| `Ritual Teacher Contract 2025 .docx` | 2025-12-05 | reference |
| `Ritual_Dashboard_Project_Plan_v1.1.docx` | 2026-03-01 | superseded by v1.3 |
| `Ritual_Dashboard_Project_Plan_v1.2.docx` | 2026-03-01 | superseded by v1.3 |
| `Ritual_KPI_Library_v1.0.docx` | 2026-03-01 | superseded by v1.2 |
| `Ritual_KPI_Library_v1.1.docx` | 2026-03-01 | superseded by v1.2 |
| `Ritual_Studios_Structured_Proposal_With_TOC.docx` | 2025-11-14 | historical |
| `Studio_Systems_Roadmap.html` | 2026-01-25 | historical (January 2026) |
| `Summary of meeting 6-Jan-26 Mark Rose.docx` | 2026-02-17 | reference — source of owner goals (S2) |
| `Teacher payrates extract Dec 2025.docx` | 2026-01-26 | historical (pay rates now in Reference Data) |
| `Teacher_Substitution_Build_Prompts.md` | 2026-06-22 | historical |
| `The uploaded document also discussed the need for.docx` | 2025-11-14 | historical |
| `To Do list from 12-12-25.docx` | 2025-12-17 | historical |
| `UI_INVENTORY.md` | 2026-06-15 | reference (June 2026) |
| `Xero_OAuth_Setup.md` | 2026-04-12 | active (reference) |
