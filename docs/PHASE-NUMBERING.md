# Phase numbering — canonical disambiguation

**Date:** 2026-06-02
**Status:** active — canon
**Purpose:** "Phase 5" (and several other phase numbers) mean different things in
different documents. This file is the single reference that says which is which.
Cite it whenever a phase number is ambiguous.

---

## Why this exists

Four parallel workstreams each adopted their own "Phase N" numbering. The numbers
overlap but do **not** refer to the same things. Before this file, "roll out
Phase 5" was genuinely ambiguous — it pointed at four different pieces of work.

## The four phase schemes

### A. Merger programme phases (0–7)

Defined in `Ritual_Studio_Ops/docs/Ritual_Studio_Ops_Merger_Plan_v2.md`. The
programme-level roadmap for merging Teacher Management and Cover Management into
Ritual Studio Ops.

| Phase | Meaning |
|---|---|
| 0 | Mobilisation (Momence code lifted in; docs governance scaffold) |
| 1 | Schema reconciliation (+ empty Phase-7 mirror tables) |
| 2 | Unified shell, read-only |
| 3 | Pipeline re-pointing (cover Python moved to `services/cover/`) |
| 4 | Write-enable and admin parity |
| **5** | **Parallel run and reconciliation** (`scripts/reconcile.py`, `test_phase5.py`, two-week soak) |
| 6 | Cutover and retirement of the legacy apps |
| 7 | Momence-in-Supabase (post-cutover) |

"Retire at Phase 6", used throughout `SOURCE_OF_TRUTH.md`, always means **this**
scheme's Phase 6.

### B. Cover Management feature phases (1–5, +6)

The build phases of the Cover Management / offer-matching feature set, each with a
`PHASE-N-*-DESIGN.md` under `Ritual_Cover_Management/`.

| Phase | Meaning | State |
|---|---|---|
| 1 | Auth + role-based permissions | shipped |
| 2 | Dedup | shipped |
| 3 | Dashboard | shipped |
| 4 | Offer matching | shipped 2026-06-02 |
| **5** | **In-Portal User Administration** | **DESIGN superseded — see `PHASE-5-USER-ADMIN-DESIGN.md` revision notice** |
| 6 | (placeholder) audit log / polish | not started |

When earlier conversations said "the next stage is Phase 5", they meant **this**
scheme's Phase 5 (In-Portal User Administration).

### C. Merged-app v2 build iterations (1–11+)

Informal iteration tags used in `CHANGELOG.md` entries and the
`rso_deploy_phaseN.bat` / `rso_git_phaseN.bat` scripts (e.g. "Phase 6", "Phase 7",
"Phase 10", "Phase 11"). These count deploy iterations of
`app/ritual-studio-ops-v2.html`, not programme milestones. They are **not** the
same as scheme A. Treat them as build-log labels only.

### D. Auth-work sub-phases (2026-05-09)

Inside the 2026-05-09 auth work, "Phase 4" referred to per-user permission
overrides within that day's design. Historical; do not reuse.

---

## Quick rule

- **"Retire at Phase 6"** → scheme A (merger programme).
- **"Phase 5 user admin" / "roll out Phase 5"** (in the User-Admin context) → scheme B.
- **"Phase 10/11" in a changelog entry** → scheme C (v2 build iteration).
- Any other use → state the scheme explicitly.

## Recommendation

New work should stop minting fresh "Phase N" labels. Reference scheme A for
programme milestones and name features explicitly otherwise (e.g. "User Admin
build", not "Phase 5").
