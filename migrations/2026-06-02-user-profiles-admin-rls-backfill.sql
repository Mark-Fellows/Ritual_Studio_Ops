-- =====================================================================
-- 2026-06-02-user-profiles-admin-rls-backfill.sql
-- ---------------------------------------------------------------------
-- DOCUMENTATION / PARITY ONLY. These objects are ALREADY LIVE on the
-- shared Supabase project rfjygyqijwgkmxboddup. They were applied
-- directly (outside the migration files) to make the merged-app v2
-- user-management UI work, and were captured in NO migration in either
-- repo. This file records them verbatim (verified live via pg_policy /
-- pg_proc on 2026-06-02) so the repository matches the database.
--
-- It is idempotent and changes nothing on the live DB. Do NOT treat it
-- as the forward plan: it is SUPERSEDED by the User-Admin build, which
-- replaces the hard-coded role checks with the fine-grained
-- `admin.users.manage` permission via has_admin_users_manage(), granted
-- to BOTH developer and administrator (decision 2026-06-02). See
-- docs/USER-ADMIN-BUILD-SPEC.md. Discovered during the 2026-06-02
-- documentation-consistency audit; see LESSONS_LEARNED L-MG-20.
-- =====================================================================

BEGIN;

-- Recursion-safe role lookup used by the policies below. Reads
-- user_profiles as the function owner (SECURITY DEFINER), so a policy ON
-- user_profiles that calls it does not re-enter RLS (avoids L-TM-04).
CREATE OR REPLACE FUNCTION public.get_my_role()
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER AS $fn$
  SELECT role FROM user_profiles WHERE user_id = auth.uid() LIMIT 1;
$fn$;

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can read own profile" ON public.user_profiles;
CREATE POLICY "Users can read own profile"
    ON public.user_profiles FOR SELECT TO public
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Developers and admins can read all profiles" ON public.user_profiles;
CREATE POLICY "Developers and admins can read all profiles"
    ON public.user_profiles FOR SELECT TO public
    USING (get_my_role() = ANY (ARRAY['developer','administrator']));

DROP POLICY IF EXISTS "Developers can insert profiles" ON public.user_profiles;
CREATE POLICY "Developers can insert profiles"
    ON public.user_profiles FOR INSERT TO public
    WITH CHECK (get_my_role() = 'developer');

DROP POLICY IF EXISTS "Developers can update profiles" ON public.user_profiles;
CREATE POLICY "Developers can update profiles"
    ON public.user_profiles FOR UPDATE TO public
    USING (get_my_role() = 'developer');

DROP POLICY IF EXISTS "Developers can delete profiles" ON public.user_profiles;
CREATE POLICY "Developers can delete profiles"
    ON public.user_profiles FOR DELETE TO public
    USING (get_my_role() = 'developer');

COMMIT;

-- NOTE the current gap (closed by the User-Admin build, not here):
-- administrator can READ all profiles but CANNOT insert/update/delete.
-- So today an administrator cannot actually manage users despite the
-- 2026-06-02 decision. The build spec's 5.0 migration replaces these
-- 'developer'-only write policies with has_admin_users_manage() checks.
