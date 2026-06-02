# User Admin / RBAC unification — handover (2026-06-03)

Autonomous session summary. Goal: roll out User Admin (Phase 5.0/5.1/5.2) and merge the
two authorization regimes onto one model. **Quality-first: nothing was pushed/deployed.**

## TL;DR status

| Layer | State |
|---|---|
| 5.0 security foundation (DB) | **APPLIED to live DB + verified** |
| Admin RPCs + user-admin RLS (DB) | **APPLIED + verified (guard tested)** |
| Security hardening (DB) | **APPLIED + verified** |
| 5.1 app changes (v2 + portal) | **Code-complete, `node --check` passes — NOT pushed, needs browser test** |
| 5.2 override tree UI | **Delivered as a ready-to-integrate snippet — not yet injected** |
| Git commit / deploy | **NOT done** — sandbox cannot write `.git`; a push auto-deploys all apps |

## What was applied to the shared database (rfjygyqijwgkmxboddup)

Backed up first to `backups/rbac-2026-06-02/` (snapshot + `ROLLBACK.sql` + app `.pre` copies + git HEADs).

1. `rbac_unification_backbone_2026_06_02` — +11 permissions (teachers/grades/bookings/
   applicants parents+leaves, admin.users.manage); leaf grants; `user_permission_overrides`
   table; `v_user_permissions_resolved` view; `has_admin_users_manage()`. Verified:
   permissions 26→37, developer→37, administrator→29, no parent-cascade over-grant.
2. `user_admin_rpcs_and_rls_2026_06_02` — `admin_invite_user`, `admin_set_user_role`,
   `admin_set_user_permission`, `admin_remove_user` (SECURITY DEFINER, permission-checked,
   self-protection); `user_profiles` writes switched developer-only → `has_admin_users_manage()`
   (administrator can now manage users); admin write policies on `user_permission_overrides`
   and `role_permissions`. Guard tested: non-admin → "Permission denied".
3. `user_admin_harden_grants_2026_06_02` — pinned `search_path` on the helper; revoked anon
   EXECUTE on the admin RPCs + helper, granted to authenticated. (From the security advisor.)

Backward compatible: `v_role_permissions_resolved` is untouched, so the **currently deployed**
app keeps working unchanged until the new JS is deployed.

## What changed in the app (staged locally, NOT pushed)

- `app/ritual-studio-ops-v2.html`: `resolvedPerms` set loaded from `v_user_permissions_resolved`;
  `hasPerm()` + `rpc()` helpers; admin gate `can('canManageUsers')` → `hasPerm('admin.users.manage')`;
  invite now attaches profile+role via `signInWithOtp` + `admin_invite_user` (Option A);
  role-change/delete routed through `admin_set_user_role` / `admin_remove_user` (onclicks pass
  `user_id`). `node --check` passes.
- `app/index.html`: permission read swapped to `v_user_permissions_resolved`. **Recovered from a
  pre-existing working-tree truncation first** (HEAD was intact; see L-MG-21). `node --check` passes.
- `app/_user-admin-5.2-overrides.snippet.js`: per-user override tree UI (validated). Integration
  steps are in the file header.

## What YOU need to do (in order)

1. **Resolve the open service-key incident** (`Ritual_Cover_Management/SECURITY-INCIDENT-2026-06-02-exposed-keys.md`) before exposing more admin surface.
2. **Browser-test** the staged app locally (or a preview) signed in as **developer** and as a
   **test administrator**:
   - Settings/admin tools visible for both; hidden for coordinator/teacher.
   - Invite a fresh email → magic link arrives → lands with the assigned role (not guest).
   - Change a role / remove a user → succeeds; you cannot remove or self-demote yourself.
   - Portal tiles still gate correctly (reads the per-user view).
3. **Integrate 5.2** from the snippet (Edit button + modal container) and re-test overrides.
4. **Commit** both repos (the sandbox could not: `.git/index.lock` was unwritable) and **push**
   to deploy — remember a push to the Pages branch auto-builds production for all four apps, so
   deploy when you can watch it. Hard-refresh and confirm.
5. Optional cleanup: remove the dead duplicate block A in v2 (L-MG-22) and archive
   `app/ritual-studio-ops-v1.html` (fails test_phase2).

## Rollback

DB: apply `backups/rbac-2026-06-02/ROLLBACK.sql`. App: restore the `.pre` copies or `git checkout`
the recorded HEADs.

## Known pre-existing issues found (not caused by this work)

- `index.html` working-tree truncation (recovered) — L-MG-21.
- v2 duplicate function blocks — L-MG-22.
- Many tables with RLS disabled / permissive policies, `teacher_directory` SECURITY DEFINER view,
  auth OTP expiry, leaked-password protection off — all pre-existing (security advisor). Out of scope.
- `teachers`-table fine-grained RLS (grades vs edit vs applicants) deferred — shares one table.
