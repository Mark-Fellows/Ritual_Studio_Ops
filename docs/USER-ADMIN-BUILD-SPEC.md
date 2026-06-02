# User Admin — Build Spec (revised Phase 5)

**Date:** 2026-06-02
**Status:** DRAFT for approval — no build and no DB changes have been made.
**Supersedes:** `Ritual_Cover_Management/PHASE-5-USER-ADMIN-DESIGN.md` (2026-05-10), which
targeted the now-legacy `public/index.html` and assumed RLS was off.
**Phase scheme:** Cover-Management feature Phase 5 (see `docs/PHASE-NUMBERING.md`).
This is **not** the merger-programme Phase 5 (parallel run) or the v2 build "Phase 5" tag.

---

## 1. Purpose

Give the merged app a proper, permission-gated way to invite, list, role-change,
permission-override and remove users — replacing the current hard-coded
`developer`-only gating with the fine-grained `admin.users.manage` permission held
by **developer and administrator**.

## 2. Decisions locked (2026-06-02)

- **Invite mechanism: Option A** — the portal JS calls `admin_invite_user` (RPC) to
  create/validate the `user_profiles` row, then calls
  `supabase.auth.signInWithOtp({ email, options:{ shouldCreateUser:true } })` from the
  admin's session to send the magic link. No new server infrastructure; same security
  profile as existing self-login. This is already the pattern in `sendUserInvite`.
- **`admin.users.manage` granted to `developer` AND `administrator`** at launch.
- **Self-protection: UI block + SQL safety net** — cannot deny your own
  `admin.users.manage` / `system.admin`, and cannot remove your own account.
- **View rename ships with the JS** in one coordinated change (small disruption window).
- **Delete-only at launch**; suspension flag deferred to 5.3.

## 3. Verified current state (live DB + app, 2026-06-02)

All confirmed by direct inspection — do not re-trust the old design over this section.

**Database (`rfjygyqijwgkmxboddup`)**

- Roles in `role_permissions`: `administrator, coordinator, developer, teacher, trainee`.
- `permissions`: 26 rows; columns `code, parent_code, category, description`; categories
  `dashboard, index, system, timetable`; `system` codes are `system.admin`, `user.signout`.
- Resolver `v_role_permissions_resolved` exists and special-cases **developer = all 26**;
  administrator resolves to 23.
- **Absent** (confirmed): `admin.users.manage` row, `user_permission_overrides` table,
  `v_user_permissions_resolved` view, `has_admin_users_manage()`, and all admin RPCs.
- `user_profiles` columns: `id, user_id, email, role, teacher_id, created_at,
  first_name, last_name, campaign_role`. No `last_sign_in`, no `is_active`.
- Recursion-safe helper exists: `get_my_role()` =
  `SELECT role FROM user_profiles WHERE user_id = auth.uid() LIMIT 1` (SQL, STABLE,
  SECURITY DEFINER).
- Live RLS on `user_profiles` (recorded in
  `migrations/2026-06-02-user-profiles-admin-rls-backfill.sql`):
  - SELECT own (`auth.uid() = user_id`)
  - SELECT all when `get_my_role() IN (developer, administrator)`
  - INSERT / UPDATE / DELETE only when `get_my_role() = 'developer'`
  - **Gap:** administrator cannot currently write — so cannot actually manage users.

**App — two different authorization models (must be reconciled)**

- **Portal `app/index.html`** is permission-driven: loads
  `v_role_permissions_resolved?role=eq.<role>` and gates tiles via `data-perm="..."`.
- **Merged app `app/ritual-studio-ops-v2.html`** (where the user-admin UI lives) is
  **not** permission-driven. It uses a hard-coded `ROLES` object with capability
  booleans and `can('canManageUsers')` (true for `developer` only). Existing functions:
  `loadUserProfiles`, `sendUserInvite` (signInWithOtp), `addNonTeacherUser`
  (`create-user` Edge Function), `deleteUser` (`dbDelete`), `updateUserRole` (`dbPatch`),
  helpers `dbGet/dbPost/dbPatch/dbDelete`, gate `can()`.

**Consequence:** 5.1 is mostly a *retarget/harden* of an existing UI, and v2 must start
reading resolved permissions so the cog/admin actions gate on `admin.users.manage`
rather than the hard-coded `canManageUsers`.

## 4. Target & guardrails

- **Edit only:** `app/ritual-studio-ops-v2.html` (admin UI), `app/index.html` (switch
  the permission read to the new view), and one new migration under
  `Ritual_Studio_Ops/migrations/`.
- **Must NOT edit:** any `Ritual_Cover_Management/public/*` legacy screen, the legacy
  Teacher Management app, or `.env`. (`SOURCE_OF_TRUTH.md`.)
- **Shared DB:** every migration is immediately live for all four apps — state the risk,
  get explicit approval, apply via Supabase MCP `apply_migration`, verify with a read.
- **Large-file discipline (L-MG-19 / L-MG-20):** `ritual-studio-ops-v2.html` is large and
  the Edit/Write tools have truncated it before. Patch via deterministic scripts, verify
  with `node --check` and a byte-count + closing-`</html>` check after every edit;
  restore from `git show HEAD:` if truncated, never from a `.bak`.
- **Resolve the open service-key exposure** (`SECURITY-INCIDENT-2026-06-02-exposed-keys.md`)
  before shipping a security feature.

---

## 5. Phase 5.0 — Security foundation (one migration)

New file: `Ritual_Studio_Ops/migrations/2026-06-0X-user-admin-foundation.sql`. Reviewed
and approved by Mark before apply. Additive and idempotent. Outline:

1. **Permission row.** Insert `admin.users.manage` into `permissions`
   (`category='system'`, `parent_code='system.admin'`, description "Manage user accounts
   and per-user permission overrides via the portal admin UI").
2. **Grants.** Insert `role_permissions` rows granting `admin.users.manage` to
   `developer` and `administrator`. (Developer already resolves to all; the explicit
   grant keeps administrator correct and is harmless for developer.)
3. **Override table.**
   ```sql
   CREATE TABLE user_permission_overrides (
     user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
     permission_code TEXT NOT NULL REFERENCES permissions(code) ON DELETE CASCADE,
     granted         BOOLEAN NOT NULL,
     granted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
     granted_by      UUID REFERENCES auth.users(id),
     PRIMARY KEY (user_id, permission_code)
   );
   ```
4. **Per-user resolver view** `v_user_permissions_resolved (user_id, permission_code)`:
   role-resolved permissions for the user's role (preserving the developer = all-26
   special case already in `v_role_permissions_resolved`), **plus** overrides where
   `granted = true`, **minus** overrides where `granted = false`. Set
   `security_invoker = true`.
5. **Admin helper** (mirrors `get_my_role()`):
   ```sql
   CREATE FUNCTION has_admin_users_manage() RETURNS boolean
   LANGUAGE sql STABLE SECURITY DEFINER AS $$
     SELECT EXISTS (SELECT 1 FROM v_user_permissions_resolved
                    WHERE user_id = auth.uid() AND permission_code = 'admin.users.manage');
   $$;
   ```
   SECURITY DEFINER bypasses RLS on the underlying tables, avoiding the
   self-recursion trap (L-TM-04).
6. **Admin RPCs** (`SECURITY DEFINER`, each begins with
   `IF NOT has_admin_users_manage() THEN RAISE EXCEPTION 'Permission denied'; END IF;`):
   - `admin_invite_user(p_email, p_role, p_first_name, p_last_name) RETURNS uuid`
     — upserts the `user_profiles` row for the (possibly pre-existing) auth user and
     returns its id. **Does not send email** — the JS does that via `signInWithOtp`
     (Option A). If the auth user does not exist yet, the row is created on first login
     by the existing login path; the RPC records the intended role/profile so the role
     is attached when they land. (Implementation detail to settle in code review:
     whether to pre-create the profile keyed on email or reconcile on first login, matching
     the existing `approve-applicant` reconciliation pattern.)
   - `admin_set_user_role(p_user_id, p_role) RETURNS void`
   - `admin_set_user_permission(p_user_id, p_permission_code, p_state) RETURNS void`
     — `p_state in ('inherit','granted','denied')`; `inherit` deletes the override row.
     Refuses to deny `admin.users.manage` / `system.admin` for `auth.uid()` (SQL safety net).
   - `admin_remove_user(p_user_id) RETURNS void` — deletes `user_profiles` + override
     rows; refuses to remove `auth.uid()`. Leaves `auth.users` intact for re-invite.
7. **RLS changes.**
   - Replace the three `get_my_role()='developer'` write policies on `user_profiles`
     with `has_admin_users_manage()` (so administrator can write too). Keep the two SELECT
     policies, but widen "read all" to `has_admin_users_manage()`.
   - `user_permission_overrides`: enable RLS; SELECT own, full CRUD when
     `has_admin_users_manage()`.
   - `role_permissions`: add INSERT/UPDATE/DELETE policy gated on `has_admin_users_manage()`
     (SELECT already open to authenticated).
   - `permissions`: SELECT stays open to authenticated; no writes.

**5.0 verification (read-only, before any UI):** `has_admin_users_manage()` true for Mark,
false for a coordinator; non-admin sees only their own `user_profiles` row; admin sees all;
`v_user_permissions_resolved` returns 26 for developer and the right set for administrator;
a non-admin `INSERT` into `user_profiles` fails with a policy error.

## 6. Phase 5.1 — Retarget & harden the existing v2 admin UI

UI/JS only; no schema change. In `app/ritual-studio-ops-v2.html`:

1. **Load resolved permissions.** On auth, fetch
   `v_user_permissions_resolved?user_id=eq.<uid>` into a `Set`. Add `hasPerm(code)`.
2. **Gate on the permission.** The user-management settings page and a (new or existing)
   cog/entry point become visible only when `hasPerm('admin.users.manage')`. Keep the
   `ROLES` object for cosmetic labels/colours only; stop using `canManageUsers` for the
   security gate.
3. **Route writes through the RPCs:** invite → `admin_invite_user` then `signInWithOtp`
   (Option A); role change → `admin_set_user_role`; remove → `admin_remove_user`. Replace
   the current direct `dbPatch`/`dbDelete` on `user_profiles`.
4. **Switch the portal + v2 permission reads** from `v_role_permissions_resolved` to
   `v_user_permissions_resolved` (in `index.html` tile gating and v2). Ship with the 5.0
   migration so the codebase never reads a renamed/!-existent view.

**5.1 verification:** Mark (developer) and a test administrator both see the admin UI; a
coordinator does not. Invite a fresh email — link arrives, click lands them on the tiles
with the assigned role. Role change reflects on the target's next load. Remove blocks the
next login. Tiles still gate correctly off the new view.

## 7. Phase 5.2 — Per-user permission overrides UI

Extend the per-user Edit panel: render the permission catalogue as a tree with three-state
toggles (inherit / granted / denied) per the original design §"Phase 5.2". On save, send a
diff of `admin_set_user_permission` calls. "Reset to role defaults" deletes all override
rows for the user. Self-protection blocks denying `admin.users.manage` / `system.admin`
for yourself (UI) backed by the SQL safety net in the RPC.

**5.2 verification:** grant one trainee `dashboard.actions.cancel_class` → only that
trainee sees Cancel Class. Deny it for a coordinator → button disappears for them. Reset
reverts to pure role-based access.

## 8. Phase 5.3 — Deferred polish (out of scope unless requested)

Audit log table populated by the four RPCs; `is_active` suspend flag (RLS refuses inactive
rows); last-sign-in column via a small RPC reading `auth.users.last_sign_in_at`; search /
pagination on the user list past ~30 users.

## 9. Risks & mitigations

- **Shared DB blast radius.** One migration hits all four apps. Mitigation: additive only,
  applied after explicit approval, verified by read; the view swap ships with the JS.
- **RLS recursion (L-TM-04).** Helpers are SECURITY DEFINER and read a different table than
  any policy they back. Test the non-admin self-read path explicitly.
- **View rename is a breaking change.** Until migration + JS ship together the portal reads
  an empty permission set (tiles grey, cog hidden) — acceptable degradation; keep the window
  short, or temporarily keep `v_role_permissions_resolved` as a compatibility wrapper.
- **Large-file truncation (L-MG-19/20).** Deterministic patchers + `node --check` + byte
  count after each edit; restore from `git show HEAD:`.
- **Open service-key exposure.** Resolve before shipping.

## 10. Build order & definition of done

1. Resolve the service-key incident.
2. Write the 5.0 migration → Mark reviews SQL → apply via Supabase MCP → verify (read).
3. 5.1 JS/HTML retarget + view swap → deploy to `ritual-studio-ops.pages.dev` → verify live.
4. 5.2 overrides UI → deploy → verify.
5. Commit per repo git rules; add a `CHANGELOG.md` entry; update `SCHEMA.md` and the docs
   index; append any new constraint to `LESSONS_LEARNED.md`.

**Done when:** developer and administrator can fully manage users and per-user overrides
from the merged app; all gating is enforced Postgres-side (a hostile anon/console user
cannot self-promote); the legacy `public/index.html` admin path is untouched; tests in
§5–7 pass; docs updated.

## 11. Open items for Mark

- [ ] Approve this spec and the 5.0 → 5.1 → 5.2 order.
- [ ] Approve the 5.0 migration SQL when drafted (shared-DB change).
- [ ] Confirm the service-key incident will be resolved first.
- [ ] Confirm `admin_invite_user` profile-attach approach at code-review time
      (pre-create on email vs reconcile-on-first-login, matching `approve-applicant`).
