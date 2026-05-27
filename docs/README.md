# Ritual Studio Ops — New Starter Guide

**What this project is.** Ritual Studio Ops is the merged operational application for Ritual Studios. It combines the Teacher Management system and the Cover Management pipeline into a single authenticated web application, backed by a single Supabase database. It is being built alongside the four existing projects (described below) so that users are never disrupted during the build.

---

## Where to look first

This project has several governance documents. Pick the one that matches your question:

| If you want to ... | Read |
|---|---|
| Know which file backs a given screen, and whether you might be editing the wrong copy | `docs/SOURCE_OF_TRUTH.md` |
| See how the portals, dashboards and external platforms link to each other | `docs/NAVIGATION.md` |
| Find any document across all four Ritual projects | `docs/DOCS_INDEX.md` |
| See the most recent changes to schema, code or docs | `docs/CHANGELOG.md` |
| Avoid known pitfalls before touching code | `docs/LESSONS_LEARNED.md` |
| Understand the merger plan and phases | `docs/Ritual_Studio_Ops_Merger_Plan_v2.md` |
| Review the latest setup audit and outstanding issues | `docs/AUDIT-RSO-2026-05-24.md` |
| Orient yourself as a new starter | continue reading this document |

---

## The four-project landscape

There are four Ritual technology projects. This project merges two of them. The other two continue unchanged.

### 1. Teacher Management (TM) — *being merged into RSO*

**What it does:** System of record for teacher identity. Five-role access control (developer → guest). Manages teacher profiles, grades by discipline, class history, trainee bookings and approvals.

**Where it lives:** `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Teacher_Management\`
**Production URL:** `https://ritual-teacher-management.pages.dev`
**Key file:** `ritual-teacher-management31.html` — this is the canonical version (v31) used as the basis for the RSO merged app.
**Database:** Supabase project `rfjygyqijwgkmxboddup.supabase.co` (same project as RSO)
**76 teachers** in production at Phase 0.

### 2. Cover Management (CM) — *being merged into RSO*

**What it does:** Cover-request orchestration pipeline. Seven Python stages: WhatsApp Web scraping → NLP parsing (Claude AI) → Momence cross-check → candidate scoring → WhatsApp/email notification → teacher accept/decline portal → client cancellation notification. Two HTML admin dashboards (currently anonymous-key; will become authenticated in RSO).

**Where it lives:** `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management\`
**Database:** Same Supabase project as TM and RSO.
**Key constraint:** Stage 1 currently imports the Momence API client via a `sys.path.insert` hack pointing to the MFPL OneDrive. This is replaced in Phase 3.

### 3. Ritual Dashboard — *downstream consumer, unchanged*

**What it does:** Analytics workspace. Reads the master CSV files produced by Momence_data. Contains a project plan, KPI library, and extensive Momence scraping documentation. Not rewritten as part of this programme.

**Where it lives:** `C:\Users\markj\OneDrive\Desktop\Ritual Dashboard\`
**Relationship to RSO:** Will continue reading master CSVs from `MOMENCE_DATA_DIR` throughout the merger. A future programme may migrate it to read directly from Supabase (Phase 8, deferred indefinitely).

### 4. Momence_data — *code absorbed into RSO; data stays put*

**What it does:** Upstream data ingestion. Two paths: a Selenium scraper chain (seven scripts, runs daily at 02:00 Brisbane, produces master CSVs) and an API v2 client (used by CM stage 1 for live session/member/booking queries). Confirmed working against 29,589 members and 55,035 sessions.

**Where it lives:** `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\` *(different OneDrive account — MFPL)*
**Phase 0 action:** The **code** (`momence_api_client.py`, `momence_data_service.py`, seven scrapers, `Run_Momence_Chain.bat`) moves into `Ritual_Studio_Ops/services/momence/`. The **data folders** (master CSVs, `momence_downloads/`, `Archive/`, `Log_files/`) stay at the MFPL path permanently and are referenced via `MOMENCE_DATA_DIR`.

---

## This project (Ritual Studio Ops)

**Where it lives:** `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Studio_Ops\` *(this folder)*
**Target URL:** `https://ritual-studio-ops.pages.dev` *(Cloudflare Pages project created 2026-05-22)*
**Database:** Same Supabase project as TM and CM — no new Supabase project.

### Directory structure

```
Ritual_Studio_Ops/
├── app/                          # Merged HTML/JS app (Phase 2+)
│   └── ritual-studio-ops-v1.html          # RSO merged app (Phase 2+, write-enabled Phase 4)
├── services/
│   ├── cover/                    # CM Python pipeline (Phase 3)
│   └── momence/                  # Momence_data code (Phase 0 — copy pending)
│       ├── momence_api_client.py
│       ├── momence_data_service.py
│       ├── scraper/              # Seven Selenium scripts
│       ├── Run_Momence_Chain.bat
│       ├── sync/                 # Phase 7 Supabase mirror scripts
│       └── docs/                 # Canonical Momence documentation
├── migrations/                   # SQL migrations (Phase 1+)
├── scripts/                      # Reconciliation, dry-runs (Phase 5)
├── docs/
│   ├── README.md                 # This file
│   ├── DOCS_INDEX.md             # Master document index (all four projects)
│   ├── CHANGELOG.md              # Master changelog (all four projects)
│   └── LESSONS_LEARNED.md       # Consolidated hard-won knowledge
├── .env.template                 # Copy to .env and fill in values
└── .gitignore
```

### Design rules (non-negotiable)

1. **Single Supabase project** — TM, CM, and RSO all share `rfjygyqijwgkmxboddup.supabase.co`. No new project.
2. **Authenticated by default** — no anon read paths in the merged app. The `anon_read_teacher_names` RLS policy is removed in Phase 1.
3. **Single source of truth for taxonomy** — the `disciplines` and `studios` reference tables (created in Phase 1) are the canonical lists. No hardcoded discipline arrays or studio name lists in code.
4. **Direct REST with cached JWT** — never use the Supabase JS client for data queries. Use `dbGet()`, `dbPost()`, `dbPatch()`, `dbDelete()` wrappers only. See LESSONS_LEARNED L-TM-01.
5. **Additive schema only** during parallel-run period (Phases 1–5). No destructive migrations until cutover.
6. **Version every file** — see LESSONS_LEARNED L-TM-07.
7. **Update DOCS_INDEX before closing any session** — a document not in the index does not officially exist.

### The merge phases

| Phase | Name | Weeks | Status |
|---|---|---|---|
| 0 | Mobilisation | 1 | **Complete** (2026-05-21) |
| 1 | Schema reconciliation | 2–3 | **Complete** (2026-05-21) |
| 2 | Unified shell, read-only | 4–5 | **Complete** (2026-05-22) |
| 3 | Pipeline re-pointing | 6–7 | **Complete** (2026-05-22) |
| 4 | Write-enable and admin parity | 8–9 | **Complete** (2026-05-22) |
| 5 | Parallel run and reconciliation | 10–11 | **In progress** — two-week soak; run `reconcile.py` daily |
| 6 | Cutover and retirement | 12 | Pending |
| 7 | Momence-in-Supabase | 13–18 | Pending (post-cutover) |

Full phase detail: `docs/Ritual_Studio_Ops_Merger_Plan_v2.md`.

### Database: tables at a glance

The Supabase project currently has these tables (all created pre-merger):

**From TM:** `teachers`, `class_history`, `user_profiles`, `audit_log`, `trainee_bookings`
**From CM:** `cover_requests`, `cover_candidates`, `cover_notifications`, `whatsapp_channels`, `whatsapp_messages`, `whatsapp_monitor_runs`, `system_config`, `discipline_mappings`

**Phase 1 will add:** `disciplines`, `studios`, `momence_sessions` (empty), `momence_members` (empty), `momence_bookings` (empty), `momence_sync_runs`

Full tables-and-owners matrix: see `DOCS_INDEX.md` section 7.

### Studios reference

| Studio | Active |
|---|---|
| Palm Beach | Yes |
| Robina | Yes |
| Mermaid | **No — closed/retired** |

Mermaid appears in historical Momence data. It is included in the `studios` table with `is_active = false` to preserve referential integrity.

---

## Key contacts and accounts

| Resource | Detail |
|---|---|
| Supabase project | `rfjygyqijwgkmxboddup.supabase.co` |
| TM production URL | `https://ritual-teacher-management.pages.dev` |
| RSO target URL | `https://ritual-studio-ops.pages.dev` |
| Momence data path | `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\` |

---

## Where to start

1. Read `DOCS_INDEX.md` to understand what documents exist and where.
2. Read `LESSONS_LEARNED.md` before touching any code — especially L-TM-01 through L-TM-07.
3. Read the Merger Plan v2 for phase-by-phase detail.
4. Check `CHANGELOG.md` for the most recent changes.
5. Set up your `.env` by copying `.env.template` and filling in the values.
