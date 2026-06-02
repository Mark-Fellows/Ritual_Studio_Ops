# RBAC Matrix & Authorization Unification

**Date:** 2026-06-02
**Status:** DRAFT for decision — no build, no DB changes. Numbers verified live
(`v_role_permissions_resolved`, `user_profiles`) on 2026-06-02.
**Related:** `USER-ADMIN-BUILD-SPEC.md`, `PHASE-NUMBERING.md`.

---

## 1. The decision: one model, not two

The merged system currently has **two authorization regimes**:

- **DB permission model** — the portal (`app/index.html`) reads
  `v_role_permissions_resolved` and gates tiles by permission code (`data-perm`).
- **Hard-coded capability model** — the merged app (`app/ritual-studio-ops-v2.html`)
  uses a client-side `ROLES` object of capability booleans (`canEditTeachers`,
  `canManageUsers`, …) gated by `can()`. Not enforced server-side.

**Recommendation:** make the **DB permission model the single source of truth**.
Demote `ROLES` to cosmetic use only (label + colour on the user pill). Replace every
`can('canX')` security gate with `hasPerm('code')` read from the per-user resolver
`v_user_permissions_resolved`. One model, one resolver, one place to change a grant,
all enforced in Postgres via RLS.

`system.admin` stays the **wildcard** ("implies every permission"); `developer` keeps
it and so resolves to everything. Superuser remains a one-row concept.

## 2. Roles — keep five, retire two

Live `user_profiles` usage: `teacher` (4), `developer` (2), `coordinator` (1),
`trainee` (1). `administrator` is provisioned-for (has grants) but unused. The v2
`ROLES` object also lists **`adjudicator`** and **`guest`**, which exist nowhere in the
database and are used by no one.

**Recommendation:** canonical roles = **developer, administrator, coordinator, teacher,
trainee**. Retire `adjudicator` and `guest` from the `ROLES` object. (If a view-only
non-teacher is ever needed, model it as a role with read-only grants, or as per-user
overrides, rather than reviving `guest`.)

## 3. Current live matrix (26 permissions × 5 roles)

`✓` = granted (resolved). Roles: **Dev** developer, **Adm** administrator,
**Coo** coordinator, **Tch** teacher, **Trn** trainee.

| Category | Permission code | Dev | Adm | Coo | Tch | Trn |
|---|---|:--:|:--:|:--:|:--:|:--:|
| dashboard | dashboard.read *(parent)* | ✓ | · | · | · | · |
| dashboard | dashboard.read.all | ✓ | ✓ | ✓ | ✓ | ✓ |
| dashboard | dashboard.read.own *(future)* | ✓ | · | · | · | · |
| dashboard | dashboard.actions *(parent)* | ✓ | ✓ | ✓ | · | · |
| dashboard | dashboard.actions.advanced_filters | ✓ | ✓ | ✓ | · | · |
| dashboard | dashboard.actions.approve | ✓ | ✓ | ✓ | · | · |
| dashboard | dashboard.actions.cancel_class | ✓ | ✓ | ✓ | · | · |
| dashboard | dashboard.actions.covered | ✓ | ✓ | ✓ | · | · |
| dashboard | dashboard.actions.edit | ✓ | ✓ | ✓ | · | · |
| dashboard | dashboard.actions.no_cover_needed | ✓ | ✓ | ✓ | · | · |
| dashboard | dashboard.actions.notes | ✓ | ✓ | ✓ | · | · |
| dashboard | dashboard.actions.settings | ✓ | ✓ | ✓ | · | · |
| index | index.tile *(parent)* | ✓ | ✓ | ✓ | ✓ | ✓ |
| index | index.tile.cover_dashboard | ✓ | ✓ | ✓ | ✓ | ✓ |
| index | index.tile.teacher_portal | ✓ | ✓ | ✓ | ✓ | ✓ |
| index | index.tile.studio_timetable | ✓ | ✓ | ✓ | ✓ | ✓ |
| index | index.tile.ritual_dashboard | ✓ | ✓ | ✓ | ✓ | ✓ |
| index | index.tile.momence | ✓ | ✓ | ✓ | ✓ | ✓ |
| index | index.tile.fitness_passport | ✓ | ✓ | ✓ | ✓ | ✓ |
| index | index.tile.classpass | ✓ | ✓ | ✓ | ✓ | ✓ |
| index | index.tile.ritual_website | ✓ | ✓ | ✓ | ✓ | ✓ |
| system | system.admin *(wildcard)* | ✓ | · | · | · | · |
| system | user.signout | ✓ | ✓ | ✓ | ✓ | ✓ |
| timetable | timetable.read | ✓ | ✓ | ✓ | ✓ | ✓ |
| timetable | timetable.actions *(parent)* | ✓ | ✓ | ✓ | · | · |
| timetable | timetable.actions.filters | ✓ | ✓ | ✓ | · | · |

### Seed issues to fix while we're here

- **Parent/child gap:** `dashboard.read` (the "view the dashboard at all" parent) is
  granted to **developer only**, yet `dashboard.read.all` is granted to everyone. If any
  code parent-gates, non-developers fail the parent check. Decide the intended rule and
  align the seed (likely grant `dashboard.read` to all five).
- **`dashboard.read.own`** exists but is developer-only and marked "future" — leave or drop.

## 4. The gap — capabilities with no permission yet

These v2 `ROLES` capabilities gate Teacher-Management features that have **no permission
code today**. Proposed new codes and a starting grant set (derived from the current
`ROLES` booleans; **edit these** — this is the decision surface):

| Legacy capability (v2) | Proposed permission code | Category | Dev | Adm | Coo | Tch | Trn |
|---|---|---|:--:|:--:|:--:|:--:|:--:|
| canManageUsers | **admin.users.manage** | system | ✓ | ✓ | · | · | · |
| canViewAll | **teachers.read.all** | teachers | ✓ | ✓ | ✓ | · | · |
| canEditTeachers | **teachers.edit** | teachers | ✓ | ✓ | ✓ | · | · |
| canEditOwnAvailability | **teachers.edit_own_availability** | teachers | · | · | · | ✓ | · |
| canEditGrades | **grades.edit** | grades | ✓ | ✓ | ✓ | · | · |
| canApprove | **bookings.approve** | bookings | ✓ | ✓ | ✓ | · | · |
| *(applicants workflow — new TM feature)* | **applicants.manage** | applicants | ✓ | ✓ | ✓ | · | · |

Notes:
- `admin.users.manage` differs from the old `ROLES` (which had developer-only): the
  2026-06-02 decision grants it to **developer + administrator**.
- `developer` need not be listed explicitly — `system.admin` (wildcard) covers it. The
  `✓`s above are shown for clarity; the seed only needs the non-developer grants.
- Add parent rows per category (e.g. `teachers`, `grades`, `bookings`, `applicants`) so
  the per-user override tree (build-spec §5.2) has the same hierarchical shape as today.

## 5. Proposed merged target matrix (what each role ends up with)

After unification, a role's effective set = its `role_permissions` grants, expanded by the
`system.admin` wildcard, then layered with any per-user overrides. Summary intent:

| Role | Cover dashboard | Timetable | Teachers/Grades/Bookings | User admin | Tiles |
|---|---|---|---|---|---|
| **developer** | all (via wildcard) | all | all | yes | all |
| **administrator** | read + all actions | read + filters | read all, edit, grades, approve, applicants | **yes** | all |
| **coordinator** | read + all actions | read + filters | read all, edit, grades, approve, applicants | no | all |
| **teacher** | read.all only | read only | edit own availability only | no | all |
| **trainee** | read.all only | read only | none | no | all |

This preserves today's behaviour for cover/timetable/tiles and promotes the v2 client-side
capability gates into real, server-enforced permissions.

## 6. How the merge is executed

1. **One additive migration** (after approval): insert the new permission rows (§4) with
   their `parent_code`/`category`, and the `role_permissions` grants per §4–5. Fix the
   `dashboard.read` parent seed (§3). No table drops.
2. **Per-user resolver** `v_user_permissions_resolved` (from the build spec) becomes the
   single read surface for both `index.html` and v2.
3. **v2 JS swap:** load the resolver into a `Set`; add `hasPerm(code)`; replace each
   `can('canX')` with the mapped `hasPerm('code')` (table §4); keep `ROLES` for labels only.
4. **RLS:** the feature tables (`teachers`, grades/bookings tables, `user_profiles`,
   `user_permission_overrides`) gate writes on the relevant permission via SECURITY DEFINER
   helpers, following the `get_my_role()` / `has_admin_users_manage()` pattern (avoids the
   L-TM-04 recursion trap).
5. **Ship migration + JS together** (view read is a breaking change); verify live.

## 7. Decisions needed

- [ ] Confirm canonical roles = developer, administrator, coordinator, teacher, trainee
      (retire adjudicator + guest).
- [ ] Approve (and edit) the new permission codes and grants in §4–5.
- [ ] Scope: model the Teacher-Management permissions **now** (full unification) or phase
      it — do `admin.users.manage` + the v2 resolver swap first, add `teachers/grades/
      bookings/applicants` codes in a follow-up? (Recommendation: do it in one pass so v2
      is never half-migrated, unless time-boxed.)
- [ ] Confirm the `dashboard.read` parent-grant fix.
