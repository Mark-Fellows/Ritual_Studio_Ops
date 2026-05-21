-- =============================================================
-- migrations/2026-05-merged-v1.sql
-- Phase 1: Schema reconciliation — Ritual Studio Ops
-- Date: 2026-05-21
-- Author: RSO programme (Mark Fellows / Claude)
--
-- ADDITIVE ONLY. All objects use IF NOT EXISTS / OR REPLACE.
-- No existing tables, columns, policies or data are modified.
--
-- What this migration does:
--   1. disciplines        -- canonical taxonomy reference table
--   2. studios            -- canonical studio reference table (seeded)
--   3. momence_members    -- Phase 7 mirror (empty placeholder)
--   4. momence_bookings   -- Phase 7 mirror (empty placeholder)
--   5. momence_sync_runs  -- audit log for Phase 7 sync jobs
--   6. teacher_directory  -- narrow view (id, first_name, last_name)
--
-- What this migration does NOT do:
--   - Remove anon_read_teacher_names (does not exist in this DB)
--   - Modify discipline_mappings (kept for backwards compat)
--   - Modify momence_sessions (already exists and is populated)
--   - Enable RLS on CM tables (separate decision; see note below)
--
-- RLS NOTE: 12 CM tables have RLS disabled. This migration does not
-- change that posture. The four new tables created here have RLS
-- enabled with authenticated-read-only policies (Phase 1 safe default).
-- =============================================================


-- =============================================================
-- 1. disciplines
--    Single source of truth for discipline taxonomy.
--    Codes match teachers.grades JSON keys and discipline_mappings.discipline_code.
-- =============================================================
CREATE TABLE IF NOT EXISTS public.disciplines (
    code         text        PRIMARY KEY,
    display_name text        NOT NULL,
    sort_order   integer     NOT NULL DEFAULT 0,
    is_active    boolean     NOT NULL DEFAULT true,
    created_at   timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.disciplines IS
    'Canonical discipline taxonomy. Single source of truth for all four projects. '
    'Codes must match teachers.grades JSON keys and discipline_mappings.discipline_code. '
    'Introduced in RSO Phase 1 (2026-05-21).';

-- Seed from discipline_mappings codes + teachers.grades keys
INSERT INTO public.disciplines (code, display_name, sort_order)
VALUES
    ('yoga',        'Yoga',        1),
    ('barre',       'Barre',       2),
    ('reformer',    'Reformer',    3),
    ('mat_pilates', 'Mat Pilates', 4),
    ('yin',         'Yin',         5)
ON CONFLICT (code) DO NOTHING;

ALTER TABLE public.disciplines ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "disciplines_read_authenticated"
    ON public.disciplines FOR SELECT
    TO authenticated USING (true);


-- =============================================================
-- 2. studios
--    Single source of truth for studio/location names.
--    Mermaid is seeded as is_active = false (closed/retired).
-- =============================================================
CREATE TABLE IF NOT EXISTS public.studios (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    code         text        NOT NULL UNIQUE,
    display_name text        NOT NULL,
    is_active    boolean     NOT NULL DEFAULT true,
    notes        text,
    created_at   timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.studios IS
    'Canonical studio/location reference. Single source of truth for all four projects. '
    'Mermaid is present but is_active = false (closed/retired location). '
    'Introduced in RSO Phase 1 (2026-05-21).';

INSERT INTO public.studios (code, display_name, is_active, notes)
VALUES
    ('palm_beach', 'Palm Beach', true,
     NULL),
    ('robina',     'Robina',     true,
     NULL),
    ('mermaid',    'Mermaid',    false,
     'Location closed/retired. Retained for historical data joins. '
     'Do not use in new cover requests or class schedules.')
ON CONFLICT (code) DO NOTHING;

ALTER TABLE public.studios ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "studios_read_authenticated"
    ON public.studios FOR SELECT
    TO authenticated USING (true);


-- =============================================================
-- 3. momence_members  (Phase 7 placeholder — empty until Phase 7)
-- =============================================================
CREATE TABLE IF NOT EXISTS public.momence_members (
    member_id    bigint      PRIMARY KEY,
    first_name   text,
    last_name    text,
    email        text,
    phone        text,
    tags         jsonb,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    _synced_at   timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.momence_members IS
    'One row per Momence member. Populated by services/momence/sync/sync_members.py '
    'post-Phase-7 cutover. Empty until then — the merged app reads it (returning zero rows) '
    'from Phase 2 without requiring a later migration.';
COMMENT ON COLUMN public.momence_members.member_id IS
    'Momence person ID — primary key from Momence API v2.';
COMMENT ON COLUMN public.momence_members._synced_at IS
    'Last time this row was written by the Phase 7 sync script.';

ALTER TABLE public.momence_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "momence_members_read_authenticated"
    ON public.momence_members FOR SELECT
    TO authenticated USING (true);


-- =============================================================
-- 4. momence_bookings  (Phase 7 placeholder — empty until Phase 7)
-- =============================================================
CREATE TABLE IF NOT EXISTS public.momence_bookings (
    booking_id     bigint      PRIMARY KEY,
    session_id     bigint      REFERENCES public.momence_sessions(session_id) ON DELETE CASCADE,
    member_id      bigint      REFERENCES public.momence_members(member_id)   ON DELETE CASCADE,
    status         text,
    cancelled      boolean,
    late_cancelled boolean,
    no_show        boolean,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    _synced_at     timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.momence_bookings IS
    'One row per Momence booking. Populated by services/momence/sync/sync_bookings.py '
    'post-Phase-7 cutover. Empty until then.';
COMMENT ON COLUMN public.momence_bookings.booking_id IS
    'Momence booking ID — primary key from Momence API v2.';

CREATE INDEX IF NOT EXISTS idx_momence_bookings_session
    ON public.momence_bookings(session_id);
CREATE INDEX IF NOT EXISTS idx_momence_bookings_member
    ON public.momence_bookings(member_id);

ALTER TABLE public.momence_bookings ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "momence_bookings_read_authenticated"
    ON public.momence_bookings FOR SELECT
    TO authenticated USING (true);


-- =============================================================
-- 5. momence_sync_runs  (audit log for Phase 7 sync jobs)
-- =============================================================
CREATE TABLE IF NOT EXISTS public.momence_sync_runs (
    run_id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    entity        text        NOT NULL
                  CHECK (entity IN ('sessions', 'members', 'bookings')),
    started_at    timestamptz NOT NULL DEFAULT now(),
    completed_at  timestamptz,
    rows_checked  integer,
    rows_upserted integer,
    rows_errored  integer     NOT NULL DEFAULT 0,
    run_status    text        NOT NULL DEFAULT 'running'
                  CHECK (run_status IN ('running', 'completed', 'partial', 'failed')),
    error_message text,
    run_notes     text
);

COMMENT ON TABLE public.momence_sync_runs IS
    'One row per Phase 7 sync run. Entity is sessions / members / bookings. '
    'run_status = partial means some rows failed validation (schema drift guard). '
    'Populated by services/momence/sync/sync_*.py scripts.';

CREATE INDEX IF NOT EXISTS idx_momence_sync_runs_entity
    ON public.momence_sync_runs(entity, started_at DESC);

ALTER TABLE public.momence_sync_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "momence_sync_runs_read_authenticated"
    ON public.momence_sync_runs FOR SELECT
    TO authenticated USING (true);


-- =============================================================
-- 6. teacher_directory view
--    Narrow view exposing only id, first_name, last_name.
--    Replaces the intent of the (non-existent) anon_read_teacher_names
--    policy. Access is gated by RLS on the underlying teachers table
--    (authenticated users only).
-- =============================================================
CREATE OR REPLACE VIEW public.teacher_directory AS
SELECT
    id,
    first_name,
    last_name
FROM public.teachers;

COMMENT ON VIEW public.teacher_directory IS
    'Read-only view of teacher identity: id, first_name, last_name only. '
    'Used by CM stage 1 and the RSO merged app to resolve teacher names '
    'without exposing phone, email, grades, availability, or WhatsApp details. '
    'Access is gated by RLS on public.teachers (authenticated users only). '
    'Introduced in RSO Phase 1 (2026-05-21).';


-- =============================================================
-- End of 2026-05-merged-v1.sql
-- =============================================================
