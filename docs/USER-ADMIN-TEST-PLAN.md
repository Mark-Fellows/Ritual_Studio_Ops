# User Admin / RBAC — Test Plan (re-runnable)

**Purpose:** verify the RBAC unification + User Admin (5.0/5.1/5.2) is healthy, any time.
**Last verified:** 2026-06-03 (all DB checks passed; app live via commit `999dd2a "ph 6"`).
**Project:** Supabase `rfjygyqijwgkmxboddup` (shared by all four Ritual apps).

How to use: run the SQL blocks in the Supabase SQL editor (or via the Supabase MCP
`execute_sql`), and do the browser steps signed into `ritual-studio-ops.pages.dev`.
Each test states its **expected** result. Anything else is a failure — see Rollback.

---

## A. Database — structural (copy/paste, one block)

```sql
WITH checks AS (
  SELECT 'permissions_total=37' AS chk, (SELECT count(*) FROM permissions)=37 AS ok
  UNION ALL SELECT 'new_perms_present=11', (SELECT count(*) FROM permissions WHERE code IN
    ('teachers','grades','bookings','applicants','admin.users.manage','teachers.view_all',
     'teachers.edit','teachers.edit_own_availability','grades.edit','bookings.approve','applicants.manage'))=11
  UNION ALL SELECT 'admin_has_users_manage', EXISTS(SELECT 1 FROM v_role_permissions_resolved WHERE role='administrator' AND permission_code='admin.users.manage')
  UNION ALL SELECT 'coordinator_no_users_manage', NOT EXISTS(SELECT 1 FROM v_role_permissions_resolved WHERE role='coordinator' AND permission_code='admin.users.manage')
  UNION ALL SELECT 'teacher_only_edit_own_avail', (SELECT count(*) FROM v_role_permissions_resolved WHERE role='teacher' AND permission_code LIKE 'teachers%')=1
  UNION ALL SELECT 'overrides_table', to_regclass('public.user_permission_overrides') IS NOT NULL
  UNION ALL SELECT 'user_view', to_regclass('public.v_user_permissions_resolved') IS NOT NULL
  UNION ALL SELECT 'helper_secdef_searchpath', (SELECT prosecdef AND proconfig IS NOT NULL FROM pg_proc WHERE proname='has_admin_users_manage')
  UNION ALL SELECT 'all_4_rpcs', (SELECT count(*) FROM pg_proc WHERE proname IN ('admin_invite_user','admin_set_user_role','admin_set_user_permission','admin_remove_user'))=4
  UNION ALL SELECT 'rpcs_secdef_searchpath', (SELECT bool_and(prosecdef AND proconfig IS NOT NULL) FROM pg_proc WHERE proname IN ('admin_invite_user','admin_set_user_role','admin_set_user_permission','admin_remove_user'))
  UNION ALL SELECT 'user_profiles_5_policies', (SELECT count(*) FROM pg_policies WHERE tablename='user_profiles')=5
  UNION ALL SELECT 'up_writes_use_helper', (SELECT count(*) FROM pg_policies WHERE tablename='user_profiles' AND qual LIKE '%has_admin_users_manage%')>=2
  UNION ALL SELECT 'overrides_2_policies', (SELECT count(*) FROM pg_policies WHERE tablename='user_permission_overrides')=2
  UNION ALL SELECT 'anon_cannot_exec_rpc', NOT has_function_privilege('anon','public.admin_remove_user(uuid)','EXECUTE')
  UNION ALL SELECT 'auth_can_exec_rpc', has_function_privilege('authenticated','public.admin_remove_user(uuid)','EXECUTE')
  UNION ALL SELECT 'dev_resolves_all_37', (SELECT count(*) FROM v_role_permissions_resolved WHERE role='developer')=37
  UNION ALL SELECT 'admin_resolves_29', (SELECT count(*) FROM v_role_permissions_resolved WHERE role='administrator')=29
)
SELECT chk, CASE WHEN ok THEN 'PASS' ELSE '*** FAIL ***' END AS result FROM checks ORDER BY ok, chk;
```

**Expected:** every row `PASS`. (`admin_resolves_29` assumes the seed grants are unchanged;
if you later add/remove role grants, update the expected number.)

## B. Database — migrations recorded

```sql
SELECT name FROM supabase_migrations.schema_migrations
WHERE name LIKE '%rbac%' OR name LIKE '%user_admin%' ORDER BY name;
```
**Expected:** `rbac_unification_backbone_2026_06_02`, `user_admin_harden_grants_2026_06_02`,
`user_admin_rpcs_and_rls_2026_06_02`.

## C. Database — functional: override layering (self-cleaning)

Replace the UID with any non-admin user (`SELECT user_id,email,role FROM user_profiles;`).

```sql
DO $$
DECLARE uid uuid := '<PUT-A-TEACHER-UID-HERE>'; g int; d int;
BEGIN
  INSERT INTO user_permission_overrides(user_id,permission_code,granted) VALUES (uid,'grades.edit',true)
    ON CONFLICT (user_id,permission_code) DO UPDATE SET granted=true;
  INSERT INTO user_permission_overrides(user_id,permission_code,granted) VALUES (uid,'timetable.read',false)
    ON CONFLICT (user_id,permission_code) DO UPDATE SET granted=false;
  SELECT count(*) INTO g FROM v_user_permissions_resolved WHERE user_id=uid AND permission_code='grades.edit';
  SELECT count(*) INTO d FROM v_user_permissions_resolved WHERE user_id=uid AND permission_code='timetable.read';
  DELETE FROM user_permission_overrides WHERE user_id=uid AND permission_code IN ('grades.edit','timetable.read');
  RAISE NOTICE 'grant_added=% (expect 1)  deny_removed=% (expect 0)', g, d;
END $$;
```
**Expected:** `grant_added=1  deny_removed=0`, and no override rows left for that user.

## D. Database — functional: RPC permission guard

```sql
DO $$
DECLARE r text;
BEGIN
  BEGIN PERFORM admin_set_user_role('00000000-0000-0000-0000-000000000000','teacher'); r:='NO EXCEPTION (FAIL)';
  EXCEPTION WHEN OTHERS THEN r:='blocked: '||SQLERRM; END;
  RAISE NOTICE '%', r;
END $$;
```
**Expected:** `blocked: Permission denied` (run without an admin JWT, e.g. SQL editor / service context).

---

## E. Browser — 5.1 user administration (sign in at ritual-studio-ops.pages.dev)

| # | Step | Expected |
|---|---|---|
| E1 | Sign in as **developer**; open Settings | "Admin Tools" / user list visible |
| E2 | Sign in as **administrator**; open Settings | Admin Tools visible (admin can manage users) |
| E3 | Sign in as **coordinator** (or teacher) | No Admin Tools / user-management section |
| E4 | As admin, invite a brand-new email with a role | Toast "Invite sent (role)"; magic link arrives; on first login the user lands with that role (NOT guest) |
| E5 | Change a user's role via the dropdown | Saves; target's next load reflects the new role/tiles |
| E6 | Try to change your **own** role to teacher | Blocked: "You cannot remove your own user-admin role." |
| E7 | Delete a (non-self) test user | Removed; your own row shows "You", no Delete |
| E8 | Try `/rest/v1/rpc/admin_remove_user` from the browser console as a non-admin | HTTP error / "Permission denied" |

## F. Browser — 5.2 per-user overrides (after integrating the snippet)

| # | Step | Expected |
|---|---|---|
| F1 | Open a user's **Edit** (permissions) panel | Tree of permissions grouped by parent; each row inherit/grant/deny |
| F2 | Grant a coordinator a permission their role lacks; Save | That user gains it on next load (check the tile/action appears) |
| F3 | Deny a permission their role has; Save | That user loses it on next load |
| F4 | "Reset to role defaults" | All overrides for that user removed; back to pure role access |
| F5 | Edit yourself: try to Deny `admin.users.manage` | Blocked (UI disabled + SQL safety net) |

## G. Browser — portal tiles (per-user resolver)

| # | Step | Expected |
|---|---|---|
| G1 | Sign in as each role | Tiles shown match that role's resolved permissions |
| G2 | Set a tile override (deny `index.tile.momence`) for a user | That tile disappears for them only |
| G3 | No user should have role `guest` | `SELECT count(*) FROM user_profiles WHERE role='guest';` → 0 |

---

## H. Regression / hygiene

```sql
-- No orphaned override rows pointing at missing users/permissions:
SELECT count(*) AS bad_overrides FROM user_permission_overrides o
 WHERE NOT EXISTS (SELECT 1 FROM auth.users u WHERE u.id=o.user_id)
    OR NOT EXISTS (SELECT 1 FROM permissions p WHERE p.code=o.permission_code);
-- Expected: 0

-- Every profile has a valid role:
SELECT role, count(*) FROM user_profiles GROUP BY role ORDER BY role;
-- Expected roles only: administrator, coordinator, developer, teacher, trainee (NO guest)

-- Duplicate-email profiles (data hygiene):
SELECT lower(email) AS email, count(*) FROM user_profiles GROUP BY 1 HAVING count(*)>1;
-- Expected: investigate any rows (e.g. hello@ritualstudios.com.au had two profiles on 2026-06-03)
```

Front-end build check: after any push, confirm the Cloudflare **Deployments** tab shows a
build for your commit, then hard-refresh. Quick source check (browser console on the portal):
`fetch(location.origin+'/ritual-studio-ops-v2.html').then(r=>r.text()).then(t=>console.log('hasPerm',t.includes('function hasPerm'),'invite',t.includes('admin_invite_user')))`
**Expected:** both `true`.

## I. Rollback (if a DB test fails)

Apply `backups/rbac-2026-06-02/ROLLBACK.sql` via the Supabase MCP, then re-run section A
(expect the pre-unification state: 26 permissions, no override table/view/RPCs). Restore app
files from git HEAD or the `.pre` copies (note: the index.html `.pre` is itself truncated —
use `git show HEAD:app/index.html`).
```
