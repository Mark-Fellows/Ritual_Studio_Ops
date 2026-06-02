-- =====================================================================
-- 2026-06-02-user-admin-harden-grants.sql
-- ---------------------------------------------------------------------
-- APPLIED 2026-06-02 via Supabase MCP apply_migration name
-- `user_admin_harden_grants_2026_06_02` (success; verified).
--
-- Hardening prompted by the security advisor after the RPC migration:
--   * pin search_path on the has_admin_users_manage() SQL helper;
--   * revoke EXECUTE on the admin RPCs and the helper from anon/PUBLIC,
--     grant to authenticated only. (The RPCs' internal
--     has_admin_users_manage() guard already blocked non-admins; this
--     removes the anon REST entry point as defence in depth.)
--
-- Verified post-apply: has_admin_users_manage proconfig = search_path;
-- anon EXECUTE on admin_* and helper = false; authenticated = true.
-- =====================================================================

ALTER FUNCTION public.has_admin_users_manage() SET search_path = public, pg_temp;

REVOKE EXECUTE ON FUNCTION public.admin_invite_user(text, text, text, text) FROM anon, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.admin_set_user_role(uuid, text) FROM anon, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.admin_set_user_permission(uuid, text, text) FROM anon, PUBLIC;
REVOKE EXECUTE ON FUNCTION public.admin_remove_user(uuid) FROM anon, PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_invite_user(text, text, text, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_set_user_role(uuid, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_set_user_permission(uuid, text, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_remove_user(uuid) TO authenticated;

REVOKE EXECUTE ON FUNCTION public.has_admin_users_manage() FROM anon, PUBLIC;
GRANT EXECUTE ON FUNCTION public.has_admin_users_manage() TO authenticated;
