-- =====================================================================
-- ROLLBACK.sql  —  undo the 2026-06-02 RBAC unification (backbone + follow-up)
-- ---------------------------------------------------------------------
-- Restores the auth/permission state captured in db_snapshot.json
-- (taken 2026-06-02T11:30:52Z, project rfjygyqijwgkmxboddup).
-- The unification was ADDITIVE, so rollback = drop the additions and
-- restore the original user_profiles write policies.
-- Apply via Supabase MCP apply_migration ONLY if a rollback is needed.
-- =====================================================================

BEGIN;

-- 1. Drop follow-up admin RPCs (no-op if not yet created)
DROP FUNCTION IF EXISTS admin_invite_user(text, text, text, text);
DROP FUNCTION IF EXISTS admin_set_user_role(uuid, text);
DROP FUNCTION IF EXISTS admin_set_user_permission(uuid, text, text);
DROP FUNCTION IF EXISTS admin_remove_user(uuid);

-- 2. Drop helper + per-user resolver + override table
DROP FUNCTION IF EXISTS has_admin_users_manage();
DROP VIEW IF EXISTS v_user_permissions_resolved;
DROP TABLE IF EXISTS user_permission_overrides;

-- 3. Remove the new role_permissions grants
DELETE FROM role_permissions WHERE permission_code IN (
  'admin.users.manage','teachers.view_all','teachers.edit',
  'teachers.edit_own_availability','grades.edit','bookings.approve','applicants.manage'
);

-- 4. Remove the new permission rows (leaves first, then parents)
DELETE FROM permissions WHERE code IN (
  'admin.users.manage','teachers.view_all','teachers.edit',
  'teachers.edit_own_availability','grades.edit','bookings.approve','applicants.manage'
);
DELETE FROM permissions WHERE code IN ('teachers','grades','bookings','applicants');

-- 5. Restore original user_profiles write policies (developer-only), in case
--    the follow-up migration replaced them with has_admin_users_manage().
DROP POLICY IF EXISTS "Developers can insert profiles" ON public.user_profiles;
CREATE POLICY "Developers can insert profiles" ON public.user_profiles
  FOR INSERT TO public WITH CHECK (get_my_role() = 'developer');
DROP POLICY IF EXISTS "Developers can update profiles" ON public.user_profiles;
CREATE POLICY "Developers can update profiles" ON public.user_profiles
  FOR UPDATE TO public USING (get_my_role() = 'developer');
DROP POLICY IF EXISTS "Developers can delete profiles" ON public.user_profiles;
CREATE POLICY "Developers can delete profiles" ON public.user_profiles
  FOR DELETE TO public USING (get_my_role() = 'developer');
DROP POLICY IF EXISTS "Developers and admins can read all profiles" ON public.user_profiles;
CREATE POLICY "Developers and admins can read all profiles" ON public.user_profiles
  FOR SELECT TO public USING (get_my_role() = ANY (ARRAY['developer','administrator']));

COMMIT;

-- Verify: SELECT count(*) FROM permissions;  -- expect 26
--         SELECT to_regclass('public.user_permission_overrides');  -- expect NULL
