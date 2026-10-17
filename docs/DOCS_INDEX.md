# Ritual Studio Ops — Master Documentation Index

**Canonical lookup for all active documentation across all four Ritual technology projects.**

A document is not considered created until this index is updated. If a document is not listed here, it does not officially exist. Two entries for the same topic means one is a duplicate — mark the older as `superseded` and consolidate.

Last updated: 2026-10-18 (audit against the workspace and live Supabase counts). Items marked **to confirm** exist but have not been reviewed individually. Dashboard plan and KPI versions are a best guess from the Dashboard README.
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
| Security incident: exposed API keys (2026-06-02) | CM | `Ritual_Cover_Management/SECURITY-INCIDENT-2026-06-02-exposed-keys.md` | **OPEN** | Two credentials were committed to the repository, including a Supabase service key. Rotation status is not confirmed as at 2026-10-18; owner to confirm and record here. |
| Working memory (CLAUDE.md) | CM | `Ritual_Cover_Management/CLAUDE.md` | active | Session working memory; last updated 2026-06-22 |
| Changelogs 2026-06 to 2026-08 (7 files) | CM | `Ritual_Cover_Management/CHANGELOG-2026-06-*.md`, `CHANGELOG-2026-07-03-*.md`, `CHANGELOG-2026-08-11-*.md` | to confirm | Not in the master CHANGELOG list above; see Appendix A |
| Plans and TODO (2026-06 to 2026-07) | CM | `PLAN-next-stages-2026-06-21.md`, `PLAN-phase4-offer-matching-2026-06-02-rev.md`, `PLAN-teacher-cover-app-2026-07-09.md`, `TODO-2026-06-22.md` | to confirm | Not in the list above; see Appendix A |

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
| Other Momence copies (Dashboard folder) | Ritual Dashboard | `Ritual Dashboard/docs/Momence Scrape documentation/` (8 further files, listed in Appendix B) | superseded | Checked 2026-10-18: byte-identical to the canonical copies in `services/momence/docs/`. |
| Momence fix notes, Feb 2026 (7 files) | Ritual Dashboard | `Ritual Dashboard/docs/archive/momence-fix-notes-2026-02/` (COLUMN_NAME_FIXES, DATAFRAME_FIX, DOWNLOAD_BUTTON_FIX, FIXES_APPLIED, LOGIN_FEATURE_SUMMARY, LOGIN_SETUP_GUIDE, TEST_REPORT) | archived 2026-10-18 | Dated 2026-02-11. Not canonical; kept for reference. LOGIN_SETUP_GUIDE and LOGIN_FEATURE_SUMMARY describe the earlier automated-login approach. |
| Momence setup and fix notes, kept in place (2 files) | Ritual Dashboard | `Ritual Dashboard/docs/Momence Scrape documentation/MOMENCE_FIRST_RUN_SETUP.md`, `FIX_SUMMARY.md` | to confirm | Not archived: the canonical Momence docs (`services/momence/docs/QUICK_START.md`, `TECHNICAL_DETAILS.md`, `VERIFICATION_CHECKLIST.md`) still point to them. Owner decision needed: archive them after those references are updated. |

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
| Momence scraping docs | Dashboard | `Ritual Dashboard/docs/Momence Scrape documentation/` | superseded | See section 4. |


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
| Staff Guide (Help modal) | RSO | `Ritual_Studio_Ops/app/ritual-studio-ops-v2.html` (Help modal) | active (**uncommitted**) | Static staff guide replaces the developer-guide fetch, which returned 404 and left the modal on "Loading guide...". The developer prompt guide and the workflow SVG are not published to the app. |
| Security incident, exposed keys | RSO | `Ritual_Cover_Management/SECURITY-INCIDENT-2026-06-02-exposed-keys.md` | **OPEN** | Rotation status unknown as of 2026-10-18; owner to confirm. |
| Momence and RLS security notes | RSO | `Ritual_Studio_Ops/docs/SECURITY-RLS-DISABLED-2026-06-05.md` | to confirm | Not previously indexed. |
| Portal developer notes | RSO | `Ritual_Studio_Ops/docs/PORTAL-DEVELOPER.md` | active | Referenced by the Finance row; not previously indexed. |
| Roadmap | RSO | `Ritual_Studio_Ops/docs/ROADMAP.md` | to confirm | Not previously indexed. |
| Cost tracking design | RSO | `Ritual_Studio_Ops/docs/Cost_Tracking_Design.md` | to confirm | Not previously indexed. |
| Cover auth notes | RSO | `Ritual_Studio_Ops/docs/ritual-cover-management-auth-notes.md` | to confirm | Not previously indexed. |
| Changelog 2026-05-26 (portal campaign tile) | RSO | `Ritual_Studio_Ops/docs/CHANGELOG-2026-05-26-portal-campaign-tile.md` | to confirm | Not previously indexed. |
| Migrations 2026-06-15 (campaigns release 4 and 5; margin columns; sender name) | RSO | `Ritual_Studio_Ops/migrations/2026-06-15-*.sql` (4 files) | to confirm | Not previously indexed. |
| Stray app files | RSO | `Ritual_Studio_Ops/app/v2-relay.html`, `index.html.old`, `index.html.2605` | to confirm | Not indexed; likely stale. Consider archiving. |
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

## Appendix A: Cover Management files not individually reviewed

71 `.md`/`.txt` files in `Ritual_Cover_Management/` (root only). Status to be confirmed by the owner.

| File | Last modified | Status |
|---|---|---|
| `ARCHITECTURE.md` | 2026-04-21 | to confirm |
| `backfill_fn.txt` | 2026-04-23 | to confirm |
| `Changelog WhatsApp.md` | 2026-04-13 | to confirm |
| `CHANGELOG-2026-04-13-nlp-sender-fallback.md` | 2026-04-13 | to confirm |
| `CHANGELOG-2026-04-23-avail-slots.md` | 2026-04-23 | to confirm |
| `CHANGELOG-2026-05-07-scheduled-task-setup.md` | 2026-05-07 | to confirm |
| `CHANGELOG-2026-05-08-phase1-and-resilience.md` | 2026-05-08 | to confirm |
| `CHANGELOG-2026-05-09.md` | 2026-05-09 | to confirm |
| `CHANGELOG-2026-05-11-momence-sessions-table.md` | 2026-05-11 | to confirm |
| `CHANGELOG-2026-05-16.md` | 2026-05-16 | to confirm |
| `CHANGELOG-2026-05-17.md` | 2026-05-16 | to confirm |
| `CHANGELOG-2026-06-01-whatsapp-export.md` | 2026-06-01 | to confirm |
| `CHANGELOG-2026-06-02-edge-changeover-and-resilience.md` | 2026-06-02 | to confirm |
| `CHANGELOG-2026-06-02-phase4-offer-matching.md` | 2026-06-02 | to confirm |
| `CHANGELOG-2026-06-09-backfill-button.md` | 2026-06-09 | to confirm |
| `CHANGELOG-2026-06-15-dedup-fix-api-keys-waReplyMap.md` | 2026-06-15 | to confirm |
| `CHANGELOG-2026-06-15-timetable-v2-margin-columns.md` | 2026-06-15 | to confirm |
| `CHANGELOG-2026-07-03-browser-drivability-and-daily-refresh.md` | 2026-07-04 | to confirm |
| `CHANGELOG-2026-08-11-whatsapp-logout-and-session-restore-wipe.md` | 2026-08-11 | to confirm |
| `CHANGELOG-dashboard-spinning-fix-20260520.md` | 2026-05-20 | to confirm |
| `CLAUDE.md` | 2026-06-22 | to confirm |
| `Cover management stages brief description.txt` | 2026-04-13 | to confirm |
| `cp_run_output.txt` | 2026-06-09 | to confirm |
| `DEPLOY.md` | 2026-05-07 | to confirm |
| `DEVELOPER.md` | 2026-06-15 | to confirm |
| `diag_atlogon_trigger.txt` | 2026-05-08 | to confirm |
| `diag_chat_dump.txt` | 2026-06-09 | to confirm |
| `diag_run_log.txt` | 2026-05-07 | to confirm |
| `diag_scheduled_tasks.txt` | 2026-05-07 | to confirm |
| `diag_shaye_records.txt` | 2026-05-07 | to confirm |
| `diag_teachers_dump.txt` | 2026-06-09 | to confirm |
| `HANDOFF-coverage-type-execution.md` | 2026-04-20 | to confirm |
| `HANDOFF-START-HERE.md` | 2026-04-20 | to confirm |
| `HELP.md` | 2026-05-08 | to confirm |
| `Index.md` | 2026-05-16 | to confirm |
| `INVESTIGATION-teachers-dropdown-2026-05-14.md` | 2026-05-21 | to confirm |
| `Nested_Messages.md` | 2026-05-19 | to confirm |
| `page_structure.txt` | 2026-04-13 | to confirm |
| `PHASE-2-DEDUP-DESIGN.md` | 2026-05-08 | to confirm |
| `PHASE-3-DASHBOARD-DESIGN.md` | 2026-05-08 | to confirm |
| `PHASE-4-OFFER-MATCHING-DESIGN.md` | 2026-06-21 | to confirm |
| `PHASE-5-USER-ADMIN-DESIGN.md` | 2026-06-02 | to confirm |
| `PHASES-quick-invoke.md` | 2026-04-20 | to confirm |
| `PLAN-coverage-type-feature.md` | 2026-04-20 | to confirm |
| `PLAN-next-stages-2026-06-21.md` | 2026-06-21 | to confirm |
| `PLAN-phase4-offer-matching-2026-05-16.md` | 2026-06-02 | to confirm |
| `PLAN-phase4-offer-matching-2026-06-02-rev.md` | 2026-06-02 | to confirm |
| `PLAN-teacher-cover-app-2026-07-09.md` | 2026-07-11 | to confirm |
| `post_reboot_check.txt` | 2026-05-08 | to confirm |
| `probe_chrome.txt` | 2026-05-07 | to confirm |
| `probe_chrome_tabs.txt` | 2026-05-07 | to confirm |
| `project_cover_management.md` | 2026-05-08 | to confirm |
| `q_out.txt` | 2026-04-23 | to confirm |
| `QUICKREF.md` | 2026-06-16 | to confirm |
| `README.md` | 2026-07-17 | to confirm |
| `requirements.txt` | 2026-04-20 | to confirm |
| `SCHEMA.md` | 2026-06-21 | to confirm |
| `SECURITY-INCIDENT-2026-06-02-exposed-keys.md` | 2026-06-16 | to confirm |
| `SESSION-LOG-2026-05-08-evening.md` | 2026-05-08 | to confirm |
| `SETUP.md` | 2026-06-16 | to confirm |
| `setup_browser_refresh_task.txt` | 2026-07-03 | to confirm |
| `setup_scheduled_tasks.txt` | 2026-05-28 | to confirm |
| `SIGNOFF-coverage-type-2026-04-21.md` | 2026-04-21 | to confirm |
| `SKILL-coverage-type-classification.md` | 2026-04-21 | to confirm |
| `SKILL-estimate-class-count.md` | 2026-04-13 | to confirm |
| `stage3_API_TEST_REPORT.txt` | 2026-04-14 | to confirm |
| `stage3_live_test_output.txt` | 2026-04-14 | to confirm |
| `TODO-2026-06-22.md` | 2026-06-29 | to confirm |
| `trigger_monitor_run.txt` | 2026-07-03 | to confirm |
| `TROUBLESHOOTING.md` | 2026-06-02 | to confirm |
| `WORKFLOW-SUMMARY.md` | 2026-04-20 | to confirm |

---

## Appendix B: Ritual Dashboard files not individually reviewed

Root `.md` files: 44. Files in `docs/` (top level): 42. The Momence scrape subfolder is covered in section 4. Status to be confirmed by the owner.

| File | Last modified | Status |
|---|---|---|
| `A2_ClassID_SessionID_Analysis.md` | 2026-04-26 | to confirm |
| `C1 Recommended changes 2026 30 06.md` | 2026-03-06 | to confirm |
| `C1_API_Migration_Phase1_Progress.md` | 2026-05-03 | to confirm |
| `C1_API_Migration_Plan.md` | 2026-05-03 | to confirm |
| `Changelog - 2026-04-17.md` | 2026-05-05 | to confirm |
| `Class_Margin_Calculation.md` | 2026-10-17 | to confirm |
| `COMPETITIVE_GAPS_EXECUTIVE_SUMMARY.md` | 2026-07-16 | to confirm |
| `COMPETITIVE_INTELLIGENCE_ANALYSIS.md` | 2026-07-16 | to confirm |
| `Course_Revenue_Recommended_Actions.md` | 2026-08-05 | to confirm |
| `Course_Session_Revenue_Investigation_2026-08-05.md` | 2026-08-05 | to confirm |
| `Data_Integrity_Audit_2026-04-17.md` | 2026-04-18 | to confirm |
| `Data_Integrity_Audit_Index.md` | 2026-04-26 | to confirm |
| `Data_Integrity_Audit_Stage1.md` | 2026-04-18 | to confirm |
| `Data_Integrity_Audit_Stage2.md` | 2026-04-18 | to confirm |
| `Data_Integrity_Audit_Stages3-6.md` | 2026-04-22 | to confirm |
| `Findings_Register.md` | 2026-04-26 | to confirm |
| `Memberships_Dashboard_Investigation_2026-05-01.md` | 2026-05-03 | to confirm |
| `Momence_API_Call_Reference.md` | 2026-05-03 | to confirm |
| `momence_booking_id_test.md` | 2026-04-26 | to confirm |
| `Post Stage 8 Integrity Audit.md` | 2026-04-26 | to confirm |
| `Post Stage 8.9 Close-Out Audit.md` | 2026-04-27 | to confirm |
| `QC_Inspection_2026-04-26.md` | 2026-04-26 | to confirm |
| `Reconciliation_20260323.md` | 2026-03-23 | to confirm |
| `SCHEDULING_ENGINE_QUICK_START.md` | 2026-07-16 | to confirm |
| `SCHEDULING_OPTIMISATION_FRAMEWORK.md` | 2026-07-16 | to confirm |
| `Setup_Summary.md` | 2026-04-02 | to confirm |
| `Stage 8-5 Changes.md` | 2026-04-26 | to confirm |
| `Stage6_Owner_Decisions_BA_Review.md` | 2026-04-26 | to confirm |
| `Stage7_Changelog.md` | 2026-04-26 | to confirm |
| `Stage8.1_Changelog.md` | 2026-04-26 | to confirm |
| `Stage8.4_Changelog.md` | 2026-04-26 | to confirm |
| `Stage8.5_Changelog.md` | 2026-04-26 | to confirm |
| `Stage8.5_Investigation_fp_unmatched.md` | 2026-04-26 | to confirm |
| `Stage8.6_Changelog.md` | 2026-04-26 | to confirm |
| `Stage8.7_Changelog.md` | 2026-04-26 | to confirm |
| `Stage8.8_Investigation_stale_collectors.md` | 2026-04-27 | to confirm |
| `Stage8.9_Changelog.md` | 2026-04-27 | to confirm |
| `Stage9.0_Changelog.md` | 2026-05-03 | to confirm |
| `WEEKLY_RECOMMENDATION_TRACKER.md` | 2026-07-16 | to confirm |
| `WEEKLY_REPORT_IMPLEMENTATION_GUIDE.md` | 2026-06-19 | to confirm |
| `WEEKLY_REPORT_SAMPLE.md` | 2026-06-21 | to confirm |
| `WEEKLY_REPORT_SAMPLE_UPDATED.md` | 2026-06-21 | to confirm |
| `weekly_report_template.md` | 2026-06-26 | to confirm |
| `Xero Backfill & Financial Model Update — Session Summary.md` | 2026-05-29 | to confirm |
| `12-12 Meeting- Defining Mark's Role and Operational Strategy.docx` | 2025-12-12 | to confirm |
| `12-12 Meeting- Defining Mark's Role and Operational Strategy.pdf` | 2025-12-12 | to confirm |
| `C1 Recommended changes 2026 30 06.md` | 2026-04-12 | to confirm |
| `CGPT ideas for campaign maangement Jan 2026.docx` | 2026-01-06 | to confirm |
| `Class change suggestions wc 12Jan26.docx` | 2026-01-13 | to confirm |
| `Cloudflare_GitHub_Deployment_Guide.md` | 2026-04-12 | to confirm |
| `DAILY_EXPORT_CHECKLIST.md` | 2026-06-20 | to confirm |
| `DAILY_PIPELINE_AUTOMATION.md` | 2026-06-19 | to confirm |
| `DAILY_WORKFLOW_OVERVIEW.md` | 2026-06-19 | to confirm |
| `Dashboard_Data_Fixes_2026-04-12.md` | 2026-04-12 | to confirm |
| `Draft Quarterly Agenda for Ritual v1.docx` | 2026-01-08 | to confirm |
| `KPI_Drilldown_Design_v1.0.md` | 2026-06-15 | to confirm |
| `manual and automatic processes, procedures, and work instructions for the studio.docx` | 2026-02-09 | to confirm |
| `Meeting notes 26 01 19.docx` | 2026-01-19 | to confirm |
| `Meeting notes 27 01 19.docx` | 2026-01-27 | to confirm |
| `Meeting notes February 4th 2026.docx` | 2026-02-04 | to confirm |
| `Membership_Attendance_Report_Documentation.docx` | 2026-03-31 | to confirm |
| `Mermaid lease.docx` | 2026-01-08 | to confirm |
| `Minutes of 4 February 2026.docx` | 2026-02-12 | to confirm |
| `Notes on Cash improvement.docx` | 2026-03-25 | to confirm |
| `Notes on Cash improvement.txt` | 2026-03-25 | to confirm |
| `Proposal 14 November 2025.docx` | 2025-11-14 | to confirm |
| `Proposal 20 November 2025.docx` | 2025-11-26 | to confirm |
| `QUICK_REFERENCE.md` | 2026-06-19 | to confirm |
| `Ritual notes and clippings.docx` | 2025-11-15 | to confirm |
| `Ritual notes.docx` | 2025-11-14 | to confirm |
| `Ritual Studio -  A Strategic Framework for Operational Excellence.docx` | 2025-12-17 | to confirm |
| `RITUAL STUDIO --  ASANA ARCHITECTURE FOR OPERATIONAL TURNAROUND.docx` | 2025-12-18 | to confirm |
| `Ritual Teacher Contract 2025 .docx` | 2025-12-05 | to confirm |
| `Ritual_Dashboard_Project_Plan_v1.1.docx` | 2026-03-01 | to confirm |
| `Ritual_Dashboard_Project_Plan_v1.2.docx` | 2026-03-01 | to confirm |
| `Ritual_KPI_Library_v1.0.docx` | 2026-03-01 | to confirm |
| `Ritual_KPI_Library_v1.1.docx` | 2026-03-01 | to confirm |
| `Ritual_Studios_Structured_Proposal_With_TOC.docx` | 2025-11-14 | to confirm |
| `Studio_Systems_Roadmap.html` | 2026-01-25 | to confirm |
| `Summary of meeting 6-Jan-26 Mark Rose.docx` | 2026-02-17 | to confirm |
| `Teacher payrates extract Dec 2025.docx` | 2026-01-26 | to confirm |
| `Teacher_Substitution_Build_Prompts.md` | 2026-06-22 | to confirm |
| `The uploaded document also discussed the need for.docx` | 2025-11-14 | to confirm |
| `To Do list from 12-12-25.docx` | 2025-12-17 | to confirm |
| `UI_INVENTORY.md` | 2026-06-15 | to confirm |
| `Xero_OAuth_Setup.md` | 2026-04-12 | to confirm |
