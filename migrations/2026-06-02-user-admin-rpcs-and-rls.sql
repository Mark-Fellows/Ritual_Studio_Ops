-- =====================================================================
-- 2026-06-02-user-admin-rpcs-and-rls.sql
-- ---------------------------------------------------------------------
-- APPLIED 2026-06-02 via Supabase MCP apply_migration name
-- `user_admin_rpcs_and_rls_2026_06_02` (success; verified, guard tested).
-- Follow-up to 2026-06-02-rbac-unification-backbone.sql. Adds the admin
-- write surface for User Admin (5.0/5.1/5.2) and tightens user-admin RLS
-- onto the admin.users.manage permission. Shared DB (rfjygyqijwgkmxboddup)
-- — applied via Supabase MCP after approval; verify after.
--
-- VERIFIED PRE-CONDITIONS (2026-06-02):
--   * user_profiles PK is (id); NO unique on user_id -> RPCs use explicit
--     exists-then-update, NOT ON CONFLICT (user_id).
--   * user_profiles has role + campaign_role CHECK constraints (role values
--     validated by the DB as well as in-RPC).
--   * has_admin_users_manage() and v_user_permissions_resolved exist (backbone).
--   * developer holds admin.users.manage via the system.admin wildcard, so
--     existing developer-driven writes keep working after the policy switch.
--
-- DELIBERATELY DEFERRED (needs a dedicated design pass; do NOT bolt on here):
--   * Per-column / per-action RLS on `teachers` to separate teachers.edit vs
--     grades.edit vs applicants.manage — they share one table, so row-level
--     RLS cannot cleanly distinguish them. These stay enforced in the app
--     layer (hasPerm gating) for now; teachers table keeps its current
--     permissive authenticated CRUD policies. Tracked in USER-ADMIN-BUILD-SPEC.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. user_profiles: switch writes from developer-only to admin.users.manage
--    (so administrator can manage users too; developer still passes via wildcard).
-- ---------------------------------------------------------------------
DROP POLICY IF EXISTS "Developers and admins can read all profiles" ON public.user_profiles;
CREATE POLICY "Admins can read all profiles" ON public.user_profiles
  FOR SELECT TO public USING (has_admin_users_manage());

DROP POLICY IF EXISTS "Developers can insert profiles" ON public.user_profiles;
CREATE POLICY "Admins can insert profiles" ON public.user_profiles
  FOR INSERT TO public WITH CHECK (has_admin_users_manage());

DROP POLICY IF EXISTS "Developers can update profiles" ON public.user_profiles;
CREATE POLICY "Admins can update profiles" ON public.user_profiles
  FOR UPDATE TO public USING (has_admin_users_manage());

DROP POLICY IF EXISTS "Developers can delete profiles" ON public.user_profiles;
CREATE POLICY "Admins can delete profiles" ON public.user_profiles
  FOR DELETE TO public USING (has_admin_users_manage());
-- "Users can read own profile" (SELECT own) is left intact.

-- ---------------------------------------------------------------------
-- 2. user_permission_overrides: admins manage; users read own (read-own
--    policy already created in the backbone).
-- ---------------------------------------------------------------------
DROP POLICY IF EXISTS "overrides_admin_all" ON public.user_permission_overrides;
CREATE POLICY "overrides_admin_all" ON public.user_permission_overrides
  FOR ALL TO public USING (has_admin_users_manage()) WITH CHECK (has_admin_users_manage());

-- ---------------------------------------------------------------------
-- 3. role_permissions: admins may edit role grants (read already open).
-- ---------------------------------------------------------------------
DROP POLICY IF EXISTS "role_permissions_admin_write" ON public.role_permissions;
CREATE POLICY "role_permissions_admin_write" ON public.role_permissions
  FOR ALL TO public USING (has_admin_users_manage()) WITH CHECK (has_admin_users_manage());

-- ---------------------------------------------------------------------
-- 4. Admin RPCs (SECURITY DEFINER, fixed search_path, permission-checked,
--    self-protection). The portal JS calls these via supabase.rpc(...).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.admin_invite_user(
    p_email text, p_role text, p_first_name text, p_last_name text)
RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_uid uuid;
BEGIN
  IF NOT has_admin_users_manage() THEN RAISE EXCEPTION 'Permission denied'; END IF;
  IF p_role IS NULL OR p_role NOT IN ('developer','administrator','coordinator','teacher','trainee')
     THEN RAISE EXCEPTION 'Invalid role: %', p_role; END IF;
  -- Option A: the auth user is created by the JS signInWithOtp call first.
  SELECT id INTO v_uid FROM auth.users WHERE lower(email) = lower(p_email) LIMIT 1;
  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'No auth user exists for % yet. Send the magic link (signInWithOtp) before attaching the profile.', p_email;
  END IF;
  IF EXISTS (SELECT 1 FROM user_profiles WHERE user_id = v_uid) THEN
    UPDATE user_profiles
       SET role = p_role, first_name = p_first_name, last_name = p_last_name, email = p_email
     WHERE user_id = v_uid;
  ELSE
    INSERT INTO user_profiles (user_id, email, role, first_name, last_name)
    VALUES (v_uid, p_email, p_role, p_first_name, p_last_name);
  END IF;
  RETURN v_uid;
END $$;

CREATE OR REPLACE FUNCTION public.admin_set_user_role(p_user_id uuid, p_role text)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  IF NOT has_admin_users_manage() THEN RAISE EXCEPTION 'Permission denied'; END IF;
  IF p_role NOT IN ('developer','administrator','coordinator','teacher','trainee')
     THEN RAISE EXCEPTION 'Invalid role: %', p_role; END IF;
  -- Self-protection: do not let an admin demote themselves out of admin in one step.
  IF p_user_id = auth.uid() AND p_role NOT IN ('developer','administrator') THEN
     RAISE EXCEPTION 'You cannot remove your own user-admin role.';
  END IF;
  UPDATE user_profiles SET role = p_role WHERE user_id = p_user_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'No profile for user %', p_user_id; END IF;
END $$;

CREATE OR REPLACE FUNCTION public.admin_set_user_permission(
    p_user_id uuid, p_permission_code text, p_state text)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  IF NOT has_admin_users_manage() THEN RAISE EXCEPTION 'Permission denied'; END IF;
  IF p_state NOT IN ('inherit','granted','denied')
     THEN RAISE EXCEPTION 'Invalid state: %', p_state; END IF;
  IF NOT EXISTS (SELECT 1 FROM permissions WHERE code = p_permission_code)
     THEN RAISE EXCEPTION 'Unknown permission: %', p_permission_code; END IF;
  -- Self-protection: cannot deny your own admin/superuser permissions.
  IF p_user_id = auth.uid() AND p_state = 'denied'
     AND p_permission_code IN ('admin.users.manage','system.admin') THEN
     RAISE EXCEPTION 'You cannot deny your own % permission.', p_permission_code;
  END IF;
  IF p_state = 'inherit' THEN
    DELETE FROM user_permission_overrides
     WHERE user_id = p_user_id AND permission_code = p_permission_code;
  ELSE
    INSERT INTO user_permission_overrides (user_id, permission_code, granted, granted_by)
    VALUES (p_user_id, p_permission_code, (p_state = 'granted'), auth.uid())
    ON CONFLICT (user_id, permission_code)
      DO UPDATE SET granted = EXCLUDED.granted, granted_at = now(), granted_by = EXCLUDED.granted_by;
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.admin_remove_user(p_user_id uuid)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  IF NOT has_admin_users_manage() THEN RAISE EXCEPTION 'Permission denied'; END IF;
  IF p_user_id = auth.uid() THEN RAISE EXCEPTION 'You cannot remove your own account.'; END IF;
  DELETE FROM user_permission_overrides WHERE user_id = p_user_id;
  DELETE FROM user_profiles WHERE user_id = p_user_id;
  -- auth.users row is left intact so the email can be re-invited later.
END $$;
