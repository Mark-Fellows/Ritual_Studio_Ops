# Ritual Studio Ops — Merger Plan v2

**Date:** 2026-05-14
**Author:** Mark Fellows (with Claude as PM)
**Status:** Draft for review
**Supersedes:** v1 (2026-05-14, same day)
**Working title for merged app:** Ritual Studio Ops

> **Important note on location.** This file currently lives inside
> `Ritual_Teacher_Management` because that is the connected workspace.
> Once you create the new `Ritual_Studio_Ops` folder, move this file
> to its `docs/` directory and update the path references throughout.

## Changes from v1

Three substantive changes have been folded in following the discussion of (a) the home of Momence_data and (b) whether to replicate Momence data in Supabase.

First, Momence_data is now part of the merger from Phase 0 onwards, but only the **code** moves into the new project tree; the **data folders** stay in their current OneDrive location and are referenced via `MOMENCE_DATA_DIR`. This decouples code consolidation from a physical data move.

Second, a new **Phase 7 — Momence-in-Supabase** has been appended. It begins after Phase 6 cutover, mirrors three Momence entities only (sessions, members, bookings) using Momence's own IDs as primary keys, and leaves the report-derived data (no-shows, late cancellations, failed penalties, total sales) in CSVs for a later iteration.

Third, Phase 1's additive schema migration now also creates the three empty Phase-7 mirror tables, so the merged app can read them (returning empty) from Phase 2 without further migrations later.

---

## 1. Executive summary

There are four Ritual technology projects in play: Teacher Management (TM), Cover Management (CM), Ritual Dashboard, and Momence_data. Only TM and CM are merged into a single new operational application — **Ritual Studio Ops** — built alongside the four existing projects so users continue to be served during the build. The Dashboard remains a downstream analytics consumer. Momence_data is partially absorbed: its code moves into the new project tree at Phase 0, but its CSV data folders stay put. After cutover, a separate **Phase 7** mirrors Momence's core operational entities (sessions, members, bookings) into Supabase, using the Momence IDs as primary keys so all four projects can join data through a single SQL surface.

Documentation governance — a master index, a master changelog and a consolidated lessons-learnt — is a first-class deliverable from Phase 0. This is non-negotiable because four projects have already produced two divergent copies of the same Momence scrape documentation, and that drift will only get worse without a single index.

## 2. Scope

**In scope (literal merger):** Teacher Management (`ritual-teacher-management.pages.dev`) and Cover Management (`cover_dashboard.html`, `teacher_portal.html`, Python stages 1–7). After parallel-run testing, both are retired.

**In scope (partial absorption):** the Momence_data **code** — `momence_api_client.py`, `momence_data_service.py`, the seven scraper scripts and `Run_Momence_Chain.bat` — moves into `Ritual_Studio_Ops/services/momence/`. Its **data folders** (master CSVs, `momence_downloads/`, `Archive/`, `Log_files/`) stay at the current OneDrive path and are referenced via the `MOMENCE_DATA_DIR` environment variable.

**In scope (reconciliation, not absorption):** Ritual Dashboard remains a downstream consumer of the master CSVs. It shares the merged project's taxonomy reference tables and the master documentation index. It is not rewritten as part of this programme.

**In scope (post-cutover):** Phase 7 — Momence-in-Supabase. Three core entities mirrored (sessions, members, bookings) using Momence IDs as PKs. Report-derived data left in CSVs for a later iteration. Dashboard migration off CSVs is a follow-on programme, not part of Phase 7.

**Out of scope:** migrating away from WhatsApp Web scraping; replacing the Momence Selenium scraper with API-only ingestion; building a Power BI or BI-tool replacement for the Dashboard; redesigning the Asana operational workflow; physical relocation of the master CSV folders.

## 3. Current state — all four projects on one page

### 3.1 Teacher Management (TM)

System of record for teacher identity. Single-file HTML/JS app with five-role RBAC, served from Cloudflare Pages, authenticated against Supabase REST using cached JWTs (per the `Ritual_Teacher_App_Prompt_Guide.md` conventions). Owns `teachers`, `class_history`, `user_profiles`, `audit_log`, and the `trainee_bookings` flow added in the 2026-04-05 changelog. Provisioning via the `create-user` Edge Function with Verify JWT off. 76 teachers in production today.

### 3.2 Cover Management (CM)

Cover-request orchestration. Python stages 1–7 (Selenium WhatsApp scraping, NLP parsing, Momence cross-check, candidate scoring, WhatsApp and email notification, teacher portal accept/decline, client cancellation notification). Two anonymous-key HTML dashboards. Schema documented in `stage1\01_cover_schema.sql` introducing `cover_requests`, `cover_candidates`, `cover_notifications`, `whatsapp_channels`, `whatsapp_monitor_runs`, `discipline_mappings`, `system_config`, and extending `teachers` with `whatsapp_phone` and `contact_preference`. Stage-1 sync (`momence_teacher_sync.py`) imports the Momence_data API client from disk via a `sys.path.insert` hack — this is removed in Phase 0.

### 3.3 Ritual Dashboard

Analytics workspace. Node project structure with `modules/collection`, `modules/processing`, `dashboard/data`, `dashboard/assets`, and an extensive `docs/` tree (project plan v1.2, KPI library v1.1, a full Momence scrape documentation set, plus reference docs on the Ritual Blueprint, Asana architecture, brand guidelines and meeting notes). Reads master CSVs produced by Momence_data.

### 3.4 Momence_data

Upstream data ingestion. Two ingestion paths.

The **Selenium scraper chain** (`Run_Momence_Chain.bat`, seven scripts, daily at 02:00 Brisbane) produces master CSVs for bookings, customers, no-shows, late cancellations, failed penalties and total sales. Cookie-based authentication with a one-time manual login; ~90–110 minute total run; checkpoint/resume; three-tier logging; extensive lessons-learnt documentation including selector reliability tiers, ten named traps, and rules-for-future-development.

The **API v2 client** (`momence_api_client.py`, `momence_data_service.py`) authenticates with client credentials and exposes session, member, booking, membership and tag retrieval. Used directly by Cover Management stage 1. Confirmed working against 29,589 members and 55,035 sessions.

## 4. Where they overlap (the merger surface)

The `teachers` table is owned by Teacher Management but extended by Cover Management and read by Momence_data's stage-1 enrichment script. Discipline taxonomy is duplicated three times (TM Prompt Guide constants, CM `discipline_mappings`, Momence_data `DISCIPLINE_PATTERNS`). Studio names appear in all four projects with slightly different spellings (Mermaid only appears in Momence_data and the Dashboard). Grade semantics live in TM but are referenced by CM's `INITIAL_TEACHER_GRADE`. Two parallel copies of Momence scrape documentation now exist and have already diverged. Auth posture diverges: TM is fully authenticated; CM dashboards use anon keys; Momence_data uses a Supabase service key for writes.

## 5. Target architecture

```
+-------------------------+        +-------------------------+
|  Momence platform       |        |  WhatsApp (community)   |
+-----------+-------------+        +-------------+-----------+
            |                                    |
   API v2   |   Selenium                         |
            v                                    v
   +--------+--------+              +------------+-----------+
   | services/momence|              | services/cover         |
   | (was Momence_   |              | (was Cover_Management) |
   |  data; code     |              | stages 2-4, 6 ingest   |
   |  only — data    |              | from WhatsApp/Momence  |
   |  via env var)   |              +------------+-----------+
   +--------+--------+                           |
            |                          cover_requests / candidates
            |  master CSVs                       |
            |  (MOMENCE_DATA_DIR)                |
            v                                    |
   +--------+-----------+                        |
   | Ritual Dashboard   |                        |
   | (downstream BI;    |                        |
   |  unchanged)        |                        |
   +--------------------+                        v
                          +----------------------+------------------+
                          |        Supabase (single project)        |
                          |  Tables (Phase 1):                      |
                          |    teachers, class_history,             |
                          |    user_profiles, audit_log,            |
                          |    trainee_bookings,                    |
                          |    cover_requests, cover_candidates,    |
                          |    cover_notifications,                 |
                          |    disciplines (NEW), studios (NEW),    |
                          |    system_config, whatsapp_*            |
                          |                                         |
                          |  Tables (Phase 1 empty, Phase 7 filled):|
                          |    momence_sessions,                    |
                          |    momence_members,                     |
                          |    momence_bookings,                    |
                          |    momence_sync_runs                    |
                          +----------------------+------------------+
                                                 ^
                                                 |
                                   +-------------+--------------+
                                   |  Ritual Studio Ops          |
                                   |  (merged TM + CM single-page|
                                   |   HTML/JS app, authenticated)|
                                   +-----------------------------+
```

Five design rules govern the merged app: **single Supabase project shared with all four systems**; **authenticated by default — no anon paths in the merged shell**; **single source of truth for taxonomy — `disciplines` and `studios` reference tables consulted by all four projects**; **direct REST with cached JWT, never the Supabase JS client for queries** (the TM convention preserved verbatim); **additive schema only** during the parallel-run period.

## 6. Documentation governance (a first-class deliverable)

Documentation drift is the biggest structural risk. Four projects have already produced overlapping documents — two copies of the Momence scrape wisdom, two copies of the API reference, dashboard plans at v1.0/v1.1/v1.2, KPI libraries at v1.0/v1.1, three sets of "lessons learnt". Without a single index and changelog, each new piece of work will spawn another copy.

The merged project will own three documentation artefacts that govern all four projects.

**`DOCS_INDEX.md`** is a master index listing every active document across all four projects, with its location, owning project, last-modified date, status (active / superseded / legacy) and one-line description. It is the canonical lookup for "where is the X document". New documents are not considered created until the index is updated. The two existing copies of the Momence scrape wisdom are consolidated into one canonical copy under `services/momence/docs/` and the index lists only that one.

**`CHANGELOG.md`** is a master changelog tracking every change of consequence to schema, code, configuration or documentation across all four projects, in reverse chronological order. Entries are short — a one-line summary, the project affected, the files changed, and a link to the relevant detailed changelog or commit. The existing `CHANGELOG-2026-04-05-teacher-management.md` and `CHANGELOG-2026-04-13-nlp-sender-fallback.md` become entries in the master, not standalone files at the project root.

**`LESSONS_LEARNED.md`** consolidates the hard-won knowledge that today exists in `Momence_data_scraping_wisdom.md`, the seven "Critical Technical Constraints" in the TM Prompt Guide (navigator.locks, getSession, supabase variable name, RLS recursion, Verify JWT, esm.sh, version-every-file), the Cover Management changelog root-causes, and the investigation document patterns. New lessons learnt are appended chronologically with a problem / cause / fix / where-it-applies structure.

A scaffold for all three of these documents is part of Phase 0. They live in the new project's `docs/` folder and are updated as the standing first step of every change.

## 7. Phased plan

### Phase 0 — Mobilisation (week 1)

Create a new top-level folder `Ritual_Studio_Ops` under `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\`. Initialise a Git repository and a Cloudflare Pages site at `ritual-studio-ops.pages.dev`. Point the new site at the **existing** Supabase project.

Project skeleton structure:

```
Ritual_Studio_Ops/
├── app/                          # Merged HTML/JS app
├── services/
│   ├── cover/                    # (Phase 3) Cover Management Python stages
│   └── momence/                  # (Phase 0) Momence_data code lifted here
│       ├── momence_api_client.py
│       ├── momence_data_service.py
│       ├── scraper/              # The seven Selenium scripts
│       ├── Run_Momence_Chain.bat
│       └── docs/                 # Single canonical scrape documentation
├── migrations/                   # SQL migrations
├── scripts/                      # Reconciliation, dry-runs, scheduled tasks
├── docs/
│   ├── DOCS_INDEX.md
│   ├── CHANGELOG.md
│   ├── LESSONS_LEARNED.md
│   └── README.md
└── .env                          # Single config; MOMENCE_DATA_DIR points to existing OneDrive path
```

Move the Momence_data code into `services/momence/` (not the data folders). Consolidate the two existing copies of the Momence scrape documentation into one canonical copy under `services/momence/docs/`. Set `MOMENCE_DATA_DIR` in `.env` to the existing `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\` path. Update the seven scraper scripts to read paths from this env var rather than hardcoded values.

Scaffold the three governance documents and seed the index with every document across all four projects identified during this discovery. Write a one-page README that explains the four-project landscape to a new starter.

Verify after the code move: Cover Management's existing stage 1 still works (it currently does `sys.path.insert(0, _MOMENCE_DIR)` — update the path to the new location and confirm the dry-run still produces the expected output). The legacy CM project keeps its own copy of the API client too for the duration of the parallel run, in case rollback is needed.

Deliverable: empty project skeleton; deploy pipeline; Momence_data code relocated; documentation consolidated; populated documentation index covering all four projects; README.

### Phase 1 — Schema reconciliation (weeks 2–3)

Produce one consolidated migration that introduces shared reference tables (`disciplines`, `studios`) and one canonical view of teacher identity, while remaining additive and backwards-compatible so the four existing projects keep working. Tighten RLS on `teachers` and replace the broad `anon_read_teacher_names` policy with a column-restricted `teacher_directory` view that exposes only `id, first_name, last_name`. Add or upgrade indexes flagged in either CM or Momence_data lessons-learnt.

**Additively create the three Phase-7 mirror tables, empty.** This means `momence_sessions`, `momence_members` and `momence_bookings` exist from Phase 1 with their final shape and primary key (the Momence record ID, typed `BIGINT`), but contain no data. The merged app reads them happily — every query returns no rows. When Phase 7 fills them, no further migration is required and no app-code change is triggered. Also create the `momence_sync_runs` table mirroring the `whatsapp_monitor_runs` pattern, so ingestion health logging is ready when needed.

Coordinate with Momence_data: the seven-script chain must keep working against the upgraded schema. Run a dry parallel write into a temporary `teachers_shadow` table for one full week to verify the sync script produces the same rows. Coordinate with the Dashboard: confirm the master-CSV column shapes do not change.

Deliverable: `migrations/2026-05-merged-v1.sql`; rollback script; tables-and-owners matrix updated in `DOCS_INDEX.md`.

### Phase 2 — Unified shell, read-only (weeks 4–5)

Build the merged front-end as a single-file HTML/JS app following the TM technical conventions in full (`sbClient` naming, cached session via `onAuthStateChange`, direct REST fetches, version comment per file). Lift across the six existing TM tabs verbatim. Add **Cover Requests** and **Teacher Cover Portal** as new top-level tabs, ported from the existing CM HTML pages but now authenticated. Everything is read-only at this stage; writes are gated behind a feature flag.

Deliverable: read-only merged shell live at the staging URL with full data parity against both legacy apps.

### Phase 3 — Pipeline re-pointing (weeks 6–7)

Move the Cover Management Python stages into the new project tree under `services/cover/`. Update them to read a single `.env` (the merged-app `.env`) and write through `SUPABASE_SERVICE_KEY`. The cross-service import that Cover Management's stage 1 needs becomes a normal Python import from `services.momence.momence_api_client` rather than a `sys.path.insert` hack. Replace any anon-only assumptions. Add the `--insert-new` option to `momence_teacher_sync.py` so the merged app no longer requires manual teacher creation as a precondition. Refactor stage 1 so it uses the `disciplines` and `studios` reference tables introduced in Phase 1.

The Momence_data seven-script chain continues to run on its existing schedule; only its code location and `.env` reference have changed.

Deliverable: re-pointed pipeline; scheduled-task definitions in `scripts/`; dry-run logs in `LESSONS_LEARNED.md`.

### Phase 4 — Write-enable and admin parity (weeks 8–9)

Switch each merged-app tab from read-only to read/write, in this order: Settings & Users, Teacher Edit, Grades, Trainee Bookings/Approvals, Cover Requests, Teacher Cover Portal. After each tab is enabled, run a 48-hour soak test in which only the merged app receives writes. The two legacy apps are downgraded in their headers to "read-only recommended". Every write is wrapped in a `writeAudit()` call so the origin is traceable.

Deliverable: feature-complete merged shell; parity sign-off; legacy banners deployed.

### Phase 5 — Parallel run and reconciliation (weeks 10–11)

Two-week parallel run. Every cover request, teacher edit and approvals action happens in the merged app. A daily reconciliation report (driven by a new `scripts/reconcile.py`) compares cover-request counts, teacher edits, audit entries and trainee-booking statuses across both surfaces. Any drift is a P1 bug. Lessons captured into `LESSONS_LEARNED.md`. Dashboard team is asked to consume from the merged app's data contract for one analytics run and confirm parity.

Deliverable: reconciliation report template; two green weeks; Dashboard parity confirmation.

### Phase 6 — Cutover and retirement (week 12)

Move users to the merged URL. Banner each legacy app linking to the merged URL. Freeze deployments on TM and CM. After 30 days zero rollback, archive the two legacy folders and delete the Cloudflare Pages projects. The Momence_data and Dashboard projects continue unchanged but their documentation indexes are updated to reflect that they now read/write the unified schema.

Deliverable: cutover comms; legacy sunset notice; archived legacy folders.

### Phase 7 — Momence-in-Supabase (weeks 13–18, post-cutover)

A separate four-to-six-week workstream that fills the three Phase-1 mirror tables with live Momence data. Begun only after Phase 6 has been stable for at least two weeks with zero rollback events.

**Scope.** Three entities mirrored: `momence_sessions`, `momence_members`, `momence_bookings`. Primary key on each table is the Momence record ID itself (e.g., `momence_session_id BIGINT PRIMARY KEY`), not a Supabase UUID. Every row carries `_synced_at TIMESTAMPTZ` so freshness is visible. Soft-delete rather than hard-delete when Momence removes a record. The report-derived tables (`momence_no_shows`, `momence_late_cancellations`, `momence_failed_penalties`, `momence_total_sales`) remain in CSV form for this phase; they are a candidate for a later iteration.

**Ingestion architecture.** A new `services/momence/sync/` package containing one upsert script per entity, each callable from the existing scraper chain post-step. Initial historical backfill runs once and takes several hours due to Momence's ~100-requests-per-minute rate limit. Steady-state incremental sync runs nightly after the existing 02:00 scrape. A periodic full-resync (weekly) acts as truth-restoration against any drift. All runs log to `momence_sync_runs` exactly as the WhatsApp monitor runs do.

**Precedence rule.** Momence is the source of truth. If Supabase and Momence disagree, Momence wins. The full-resync mechanism is the corrective.

**Storage estimate.** Approximately 500 MB to 1 GB total once backfilled (55,000 sessions, 30,000 members, ~500,000 bookings). Comfortable on the Supabase paid tier.

**What this unlocks.** Cover Management's candidate scoring can read historical attendance and fill-rate data natively. Cross-domain joins like "every teacher's no-show rate by discipline and location for the last 90 days, joined to their TM grade" become single SQL statements. It also creates the foundation for an eventual Dashboard migration off the CSV pipeline (a separate follow-on programme).

**What this does NOT include.** Dashboard re-pointing off the CSV pipeline. Replacement of the Selenium scrape chain. Migration of report-derived data. These are deliberately deferred.

Deliverable: three filled mirror tables; ingestion service running on schedule; periodic full-resync proven; sync-health monitoring; lessons-learnt entries appended.

## 8. Risk register

The largest risk is that three apps now write to `teachers` during the parallel-run period — TM, CM and the merged app — and an ill-formed write from any of them corrupts a record. Mitigation: every merged-app write goes through a wrapper that records origin in `audit_log`; daily reconciliation reports flag any unexplained change; the legacy apps are downgraded to read-only in the UI from Phase 4 onwards.

The second risk is selector drift in the Momence Selenium scraper — the lessons-learnt document already records that CSS classes changed without warning in Feb 2026 and broke the pipeline for several days. Mitigation: keep the existing fallback strategy (Tier 1 href/icon selectors plus a JavaScript regex Tier 4); monitor the batch log; do not couple the merged app to the scraper's success — the merged app must remain functional when the scrape is stale.

The third risk is documentation drift continuing despite the new governance. Mitigation: a single-line check in the PR template; a Phase-0 retrospective two weeks in to check it is being followed.

The fourth risk is RLS regression. The current `anon_read_teacher_names` policy leaks all teacher PII. The Phase 1 migration must remove it the same day the `teacher_directory` view is introduced. Mitigation: a coordinated migration script that does both atomically; a rollback script that restores the old policy if the view fails.

The fifth risk is taxonomy divergence — the Dashboard uses **Mermaid** as a third location, which TM and CM do not. Mitigation: confirm whether Mermaid is a current studio, a closed location, or a room within a building. The `studios` reference table must reflect the correct answer.

The sixth risk, specific to Phase 7, is sync drift — Supabase silently diverges from Momence due to a bug in the upsert logic. Mitigation: every entity carries `_synced_at`, every run logs to `momence_sync_runs`, and a weekly full-resync acts as a forcing function to detect and correct drift. A `services/momence/sync/verify.py` script compares row counts and a sample of records nightly and alerts on mismatches > 0.1%.

The seventh risk, also specific to Phase 7, is Momence schema evolution — a field is renamed or removed and the sync code silently misses it. Mitigation: every upsert validates the payload shape against a schema snapshot stored in the repo; any unrecognised or missing field raises a warning and logs to `momence_sync_runs` with `run_status='partial'`.

## 9. Decisions you have already given me

Same Supabase project, parallel run. Working name **Ritual Studio Ops**. Deliverable as Markdown, not docx. Keep WhatsApp Web scraper for now. Four projects to consider, not two. Move Momence_data **code** into the new project at Phase 0; leave data folders where they are and reference via `MOMENCE_DATA_DIR`. Phase 7 mirrors **only three entities** — sessions, members, bookings — using Momence IDs as primary keys; runs **after Phase 6 cutover**, not in parallel.

## 10. Open decisions still needed

Four items remain to be confirmed before Phase 0 starts.

First — is **Mermaid** a current Ritual studio, a closed location, or a different concept (a room within Palm Beach or Robina)? The `studios` reference table cannot be designed without this answer.

Second — for documentation governance, do you want me to include reference docs (the Ritual Blueprint, Asana architecture, brand guidelines, meeting notes) in `DOCS_INDEX.md`, or only operational docs? My recommendation is everything; reference docs are the ones most likely to be forgotten and duplicated.

Third — is the v29 local copy of the TM single-file app the canonical version to lift across in Phase 2, or is the deployed `ritual-teacher-management.pages.dev` build authoritative? The 05-April changelog says v29 has a defensive sign-in fix and a stray overwrite removed; the deployed build may or may not have those.

Fourth — for Phase 7, is there appetite to also migrate the **Dashboard's CSV consumption** to Supabase as a follow-on Phase 8, or should that be deferred indefinitely until a separate business case justifies it? My recommendation is to defer formally; the CSV pipeline works and the Dashboard team has other priorities.

## 11. Sources

- `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Teacher_Management\Ritual_Teacher_App_Prompt_Guide.md`
- `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Teacher_Management\Ritual Studios Business Improvement teacher management v15.txt`
- `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Teacher_Management\CHANGELOG-2026-04-05-teacher-management.md`
- `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Teacher_Management\migrations\2026-04-05-add-teacher-photo-and-momence.sql`
- `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management\Cover management stages brief description.txt`
- `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management\stage1\01_cover_schema.sql`
- `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management\stage1\momence_teacher_sync.py`
- `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management\INVESTIGATION-teachers-dropdown-2026-05-14.md`
- `C:\Users\markj\OneDrive\Desktop\Ritual Dashboard\docs\Momence Scrape documentation\Momence_data_scraping_wisdom.md`
- `C:\Users\markj\OneDrive\Desktop\Ritual Dashboard\docs\Momence Scrape documentation\TECHNICAL_DETAILS.md`
- `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\MOMENCE_SKILL_USAGE_GUIDE.md`
- `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Teacher_Management\Ritual_Studio_Ops_Merger_Plan_v1.md` (predecessor)
