# Ritual Studio Ops — Source of Truth

**Date:** 2026-05-24
**Purpose:** one reference for the question "if I want a screen changed, which file is the live one?"

During the merger (Phases 1-6) the old and new systems run side by side on purpose, so most things genuinely exist in two places. This document says which copy is current, so a change never lands in a stale file.

---

## The quick rule

Every **new (merged)** screen now carries the **Ritual emblem badge**, top-left of the header.

- **Badge visible** → you are in the merged system. A change goes into a file under `Ritual_Studio_Ops/app/`.
- **No badge** → a legacy app that is being retired. Do not change it — make the change in the merged app instead.
- **By URL:** `ritual-studio-ops.pages.dev` is the new system. `ritual-teacher-management.pages.dev` and `ritual-cover-management.pages.dev` are the old ones.

(The badge appears once the new screens are deployed — see "Deploying a change" below.)

---

## Web screens — which file backs which screen

| Screen | Live URL | File to edit | Status |
|---|---|---|---|
| Management Portal (launcher) | `ritual-studio-ops.pages.dev` | `Ritual_Studio_Ops/app/index.html` | **CURRENT — new** |
| Merged app (Teachers + Cover) | `ritual-studio-ops.pages.dev/ritual-studio-ops-v2.html` | `Ritual_Studio_Ops/app/ritual-studio-ops-v2.html` | **CURRENT — new** |
| Legacy Teacher Management | `ritual-teacher-management.pages.dev` | `Ritual_Teacher_Management/ritual-teacher-management31.html` | Legacy — retire at Phase 6 |
| Legacy Cover Management portal | `ritual-cover-management.pages.dev` | `Ritual_Cover_Management/public/index.html` | Legacy — retire at Phase 6 |
| Legacy Cover Dashboard | `ritual-cover-management.pages.dev/cover_dashboard.html` | `Ritual_Cover_Management/public/cover_dashboard.html` | Legacy — retire at Phase 6 |
| Legacy Teacher Portal | `ritual-cover-management.pages.dev/teacher_portal.html` | `Ritual_Cover_Management/public/teacher_portal.html` | Legacy — retire at Phase 6 |
| Studio Timetable | `ritual-cover-management.pages.dev/studio_timetable.html` | `Ritual_Cover_Management/public/studio_timetable.html` | Still in use — not yet merged |

The merged app **was built new** — it is not a copy of the old Teacher Management app. It re-created the Teacher Management screens and added the Cover screens in one app. The old apps still exist separately and run until cutover.

---

## Backend — what is shared and what is copied

| Layer | Current location | Notes |
|---|---|---|
| Database | Supabase project `rfjygyqijwgkmxboddup` | **Single shared database** — old and new both use it. It is **not** duplicated. A database change affects every app at once. |
| Cover pipeline (Python) | `Ritual_Studio_Ops/services/cover/` | **Current.** Re-pointed here in Phase 3. The legacy stages under `Ritual_Cover_Management/` are kept only as a rollback safety net. |
| Momence code (Python) | `Ritual_Studio_Ops/services/momence/` | **Current.** Copied here in Phase 0. The Momence **data** files stay in their original OneDrive folder. |

So: the database was **not** copied (one shared project). The cover and Momence **code** was copied — the copies under `Ritual_Studio_Ops/services/` are the live ones.

---

## Copies that back nothing — never edit these

| Path | What it is |
|---|---|
| `Ritual_Studio_Ops/Ritual_Studio_Ops/` | A full duplicate of the entire project, nested inside the project. Stale (one commit behind). **Recommended for deletion.** |
| `Ritual_Studio_Ops/app/ritual-studio-ops-v1.html` | The first version of the merged app. Superseded by v2, and truncated/corrupt. |
| `Ritual_Studio_Ops/app/ritual-teacher-management31.html` | A reference snapshot copied in at Phase 0. Backs nothing. |
| `Ritual_Studio_Ops/app/cover_dashboard_ref.html` | A reference snapshot copied in at Phase 0. Backs nothing. |
| `Ritual_Studio_Ops/app/teacher_portal_ref.html` | A reference snapshot copied in at Phase 0. Backs nothing. |

If anyone edits one of these, the change will never appear on a live screen.

---

## Why there are two of everything

**Intentional.** The merger deliberately runs the new system alongside the old one (a "parallel run") so staff are never disrupted during the build. The old apps, and the legacy Python pipeline, are kept until the Phase 6 cutover and then retired. Two versions during Phases 1-6 is by design.

**Accidental.** The nested duplicate folder, `ritual-studio-ops-v1.html`, and the three reference snapshots are *not* part of that plan. They are leftovers and should be removed to stop them being edited by mistake.

---

## Deploying a change to the new screens

After editing `app/index.html` or `app/ritual-studio-ops-v2.html`, run `rso_deploy.bat`. It deploys the whole `app/` folder to `ritual-studio-ops.pages.dev`. The change (and the emblem badge) is only live once that deploy has run.
