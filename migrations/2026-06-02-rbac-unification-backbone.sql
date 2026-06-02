-- =====================================================================
-- 2026-06-02-rbac-unification-DRAFT.sql
-- ---------------------------------------------------------------------
-- APPLIED 2026-06-02 via Supabase MCP apply_migration name
-- `rbac_unification_backbone_2026_06_02` (success; verified). Shared DB
-- (rfjygyqijwgkmxboddup):
-- every change here is immediately live for ALL four Ritual apps. Do not
-- apply until Mark approves. After approval, apply via Supabase MCP
-- apply_migration and verify with the read-only checks at the bottom.
--
-- PURPOSE: collapse the two authorization regimes onto the DB permission
-- model (see docs/RBAC-MATRIX.md). This migration covers the VERIFIED
-- backbone:
--   1. extend the permission catalogue to cover the Teacher-Management
--      features v2 currently gates client-side via the ROLES object;
--   2. seed role_permissions grants per the matrix (leaf codes only);
--   3. add the per-user override table + per-user resolver view;
--   4. add the has_admin_users_manage() helper.
--
-- DELIBERATELY NOT IN THIS FILE (need a schema-audit pass first, so we do
-- not invent table names): per-table RLS write policies on the
-- teachers / grades / bookings / applicants tables, and the admin_* RPCs.
-- Those land in a follow-up migration once the feature-table schema is
-- confirmed. See docs/USER-ADMIN-BUILD-SPEC.md.
--
-- RESOLVER FACTS this migration relies on (verified 2026-06-02):
--   * v_role_permissions_resolved expands `system.admin` as a WILDCARD
--     (CROSS JOIN permissions) -> developer auto-gets every NEW code below;
--     no explicit developer grants are needed.
--   * It also cascades parent_code -> child. We therefore grant LEAF codes
--     explicitly and do NOT grant new parent codes to non-developer roles,
--     to avoid accidentally granting teachers.edit_own_availability to
--     administrators/coordinators.
--   * permissions PK = code; role_permissions PK = (role, permission_code).
--
-- NOT CHANGED HERE (separate, explicit decision): the dashboard.read parent
-- seed gap. Granting that parent would cascade dashboard.read.own to
-- teacher/trainee. Left as-is pending Mark's decision.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 1. Catalogue: new permission rows. Parents first (FK parent_code ->
--    permissions.code), then leaves. Idempotent.
-- ---------------------------------------------------------------------
INSERT INTO permissions (code, parent_code, category, description) VALUES
  ('teachers',   NULL, 'teachers',   'Teacher records area (parent)'),
  ('grades',     NULL, 'grades',     'Teacher grading area (parent)'),
  ('bookings',   NULL, 'bookings',   'Trainee bookings/approvals area (parent)'),
  ('applicants', NULL, 'applicants', 'Teacher applications area (parent)')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (code, parent_code, category, description) VALUES
  ('admin.users.manage',            NULL,         'system',     'Manage user accounts and per-user permission overrides via the portal admin UI'),
  ('teachers.view_all',             'teachers',   'teachers',   'View all teacher records (was ROLES.canViewAll)'),
  ('teachers.edit',                 'teachers',   'teachers',   'Edit teacher records (was ROLES.canEditTeachers)'),
  ('teachers.edit_own_availability','teachers',   'teachers',   'Edit own availability only (was ROLES.canEditOwnAvailability)'),
  ('grades.edit',                   'grades',     'grades',     'Edit teacher grades (was ROLES.canEditGrades)'),
  ('bookings.approve',              'bookings',   'bookings',   'Approve trainee bookings (was ROLES.canApprove)'),
  ('applicants.manage',             'applicants', 'applicants', 'Review/verify/approve/reject teacher applicants')
ON CONFLICT (code) DO NOTHING;

-- ---------------------------------------------------------------------
-- 2. Grants per RBAC-MATRIX.md (LEAF codes only; developer covered by the
--    system.admin wildcard, so it is intentionally absent here).
-- ---------------------------------------------------------------------
INSERT INTO role_permissions (role, permission_code, granted_at) VALUES
  -- administrator (locked decision: also gets user admin)
  ('administrator', 'admin.users.manage',             now()),
  ('administrator', 'teachers.view_all',              now()),
  ('administrator', 'teachers.edit',                  now()),
  ('administrator', 'grades.edit',                    now()),
  ('administrator', 'bookings.approve',               now()),
  ('administrator', 'applicants.manage',              now()),
  -- coordinator
  ('coordinator',   'teachers.view_all',              now()),
  ('coordinator',   'teachers.edit',                  now()),
  ('coordinator',   'grades.edit',                    now()),
  ('coordinator',   'bookings.approve',               now()),
  ('coordinator',   'applicants.manage',              now()),
  -- teacher
  ('teacher',       'teachers.edit_own_availability', now())
  -- trainee: none of the new codes
ON CONFLICT (role, permission_code) DO NOTHING;

-- ---------------------------------------------------------------------
-- 3. Per-user override table (build-spec 5.0 item 3).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_permission_overrides (
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    permission_code TEXT NOT NULL REFERENCES permissions(code) ON DELETE CASCADE,
    granted         BOOLEAN NOT NULL,
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    granted_by      UUID REFERENCES auth.users(id),
    PRIMARY KEY (user_id, permission_code)
);
ALTER TABLE user_permission_overrides ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "overrides_read_own" ON user_permission_overrides;
CREATE POLICY "overrides_read_own" ON user_permission_overrides
    FOR SELECT TO authenticated USING (user_id = (SELECT auth.uid()));
-- NOTE: admin write policies on this table use has_admin_users_manage()
-- and ship in the follow-up RLS/RPC migration (so the helper exists first
-- in app order). Until then, writes are service-role only.

-- ---------------------------------------------------------------------
-- 4. Per-user resolver. Reuses the verified role recursion (wildcard +
--    parent cascade), keyed by the user's role, then layers overrides:
--    + granted overrides, - denied overrides. security_invoker=true so
--    direct app reads honour the caller's RLS (a user sees only their own
--    rows unless an admin-read policy widens it).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_user_permissions_resolved AS
WITH RECURSIVE expand AS (
    SELECT rp.role, rp.permission_code AS code
      FROM role_permissions rp
    UNION
    SELECT rp.role, p.code
      FROM role_permissions rp CROSS JOIN permissions p
     WHERE rp.permission_code = 'system.admin'
    UNION
    SELECT e.role, p.code
      FROM expand e JOIN permissions p ON p.parent_code = e.code
),
role_perms AS (
    SELECT up.user_id, e.code AS permission_code
      FROM user_profiles up
      JOIN expand e ON e.role = up.role
),
with_grants AS (
    SELECT user_id, permission_code FROM role_perms
    UNION
    SELECT user_id, permission_code FROM user_permission_overrides WHERE granted = true
)
SELECT wg.user_id, wg.permission_code
  FROM with_grants wg
 WHERE NOT EXISTS (
     SELECT 1 FROM user_permission_overrides o
      WHERE o.user_id = wg.user_id
        AND o.permission_code = wg.permission_code
        AND o.granted = false
 );
ALTER VIEW v_user_permissions_resolved SET (security_invoker = true);

-- ---------------------------------------------------------------------
-- 5. Admin helper (mirrors get_my_role(): SECURITY DEFINER bypasses RLS on
--    the underlying tables, avoiding the L-TM-04 recursion trap).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.has_admin_users_manage()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER AS $fn$
  SELECT EXISTS (
    SELECT 1 FROM v_user_permissions_resolved
    WHERE user_id = auth.uid() AND permission_code = 'admin.users.manage'
  );
$fn$;

COMMIT;

-- =====================================================================
-- VERIFICATION (read-only — run after apply)
-- =====================================================================
-- New codes present (expect 11 incl. parents):
--   SELECT code, parent_code, category FROM permissions
--   WHERE category IN ('teachers','grades','bookings','applicants')
--      OR code='admin.users.manage' ORDER BY category, code;
--
-- Administrator now resolves admin.users.manage + the TM leaves; developer
-- still all; teacher gets only edit_own_availability among the new ones:
--   SELECT role, count(*) FROM v_role_permissions_resolved GROUP BY role ORDER BY role;
--   SELECT permission_code FROM v_role_permissions_resolved
--   WHERE role='teacher' AND permission_code LIKE 'teachers.%';   -- expect edit_own_availability only
--
-- Per-user resolver returns a sane set for a known admin user_id:
--   SELECT count(*) FROM v_user_permissions_resolved WHERE user_id = '<mark-uid>';
--
-- Helper:
--   SELECT has_admin_users_manage();   -- true for an admin session, false otherwise
-- =====================================================================
