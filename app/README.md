# app/

This directory contains the merged HTML/JS application.

## Phase 0 contents (reference copies)

| File | Source | Purpose |
|---|---|---|
| `ritual-teacher-management31.html` | `Ritual_Teacher_Management/` | **Canonical TM v31** — starting point for Phase 2 lift-across |
| `cover_dashboard_ref.html` | `Ritual_Cover_Management/public/cover_dashboard.html` | Reference copy — CM admin dashboard to be absorbed in Phase 2 |
| `teacher_portal_ref.html` | `Ritual_Cover_Management/public/teacher_portal.html` | Reference copy — CM teacher portal to be absorbed in Phase 2 |

## Phase 2 target

The merged app will be a single file following TM technical conventions exactly:
- Named `ritual-studio-ops-NNN.html` where NNN is the version number
- `sbClient` (not `supabase`) for the Supabase client
- Session cached via `onAuthStateChange`; never call `getSession()` after init
- All data queries via `dbGet()`, `dbPost()`, `dbPatch()`, `dbDelete()` — direct REST, never the JS client
- Version comment at top of file

See LESSONS_LEARNED L-TM-01 through L-TM-07 before starting Phase 2.
