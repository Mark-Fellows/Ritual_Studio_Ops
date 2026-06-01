-- Migration: Teacher Applications (public intake + applicant review)
-- Date: 2026-06-01
-- Project: Supabase rfjygyqijwgkmxboddup (SHARED by all four Ritual apps)
-- Design: Ritual_Teacher_Management/Ritual Teacher Management/Teacher_Applications_Design.md (rev 3)
--
-- SAFETY / SCOPE
--   Additive only (Phase 5/6 parallel-run rule): no column drops, no renames,
--   no destructive changes. Adding defaulted columns backfills existing rows
--   safely (existing teachers become status='active').
--   This database is shared - applying this is immediately live for Teacher
--   Management, Cover Management, Campaigns, Momence_data and the Dashboard.
--   RLS: no new anon policy on teachers. Public application writes go through a
--   service-role Edge Function (service role bypasses RLS), so unauthenticated
--   callers never touch teacher PII (L-CM-07). No policy references the teachers
--   table within its own qual (L-TM-04, no recursion).
--   Indexes use only IMMUTABLE expressions (no CURRENT_DATE) per L-MG-09.
--
-- ROLLBACK (manual, if ever required during parallel run - not part of apply):
--   The ADD COLUMN IF NOT EXISTS statements and the new table can be dropped,
--   but per Phase 5/6 rules destructive rollback is avoided while both apps run.

BEGIN;

-- 1) Applicant fields on the existing teachers table (all additive) -----------
ALTER TABLE public.teachers
  ADD COLUMN IF NOT EXISTS status              text        NOT NULL DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS experience_training text,
  ADD COLUMN IF NOT EXISTS teaching_style      text,
  ADD COLUMN IF NOT EXISTS video_url           text,
  ADD COLUMN IF NOT EXISTS availability_text   text,
  ADD COLUMN IF NOT EXISTS located_text        text,
  ADD COLUMN IF NOT EXISTS cv_url              text,
  ADD COLUMN IF NOT EXISTS email_verified      boolean     NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS phone_verified      boolean     NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS applied_at          timestamptz,
  ADD COLUMN IF NOT EXISTS source              text,
  ADD COLUMN IF NOT EXISTS possible_duplicate  boolean     NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS duplicate_notes     text,
  ADD COLUMN IF NOT EXISTS rejected_at         timestamptz,
  ADD COLUMN IF NOT EXISTS rejected_by         text;

-- Guard the allowed status values without breaking existing rows.
-- 'active' (live roster), 'applicant' (awaiting review/verification), 'rejected'.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'teachers_status_check'
  ) THEN
    ALTER TABLE public.teachers
      ADD CONSTRAINT teachers_status_check
      CHECK (status IN ('active','applicant','rejected'));
  END IF;
END $$;

COMMENT ON COLUMN public.teachers.status IS 'active | applicant | rejected. Existing rows default to active.';
COMMENT ON COLUMN public.teachers.source IS 'Origin of the record, e.g. public_application, asana_recruitment_import.';
COMMENT ON COLUMN public.teachers.possible_duplicate IS 'Set when email/phone matches an existing record at submission time.';

-- Index to drive the Applicants filter and to exclude applicants from the
-- live teacher lists (status is immutable-safe to index).
CREATE INDEX IF NOT EXISTS idx_teachers_status ON public.teachers (status);

-- Case-insensitive email lookup for the duplicate check (lower() is IMMUTABLE).
CREATE INDEX IF NOT EXISTS idx_teachers_email_lower ON public.teachers (lower(email));

-- 2) Email OTP store (transient; WhatsApp/SMS deferred - email channel only) ---
CREATE TABLE IF NOT EXISTS public.application_otps (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  teacher_id  uuid REFERENCES public.teachers(id) ON DELETE CASCADE,
  channel     text NOT NULL DEFAULT 'email' CHECK (channel IN ('email','whatsapp')),
  code_hash   text NOT NULL,
  expires_at  timestamptz NOT NULL,
  attempts    integer NOT NULL DEFAULT 0,
  consumed_at timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_application_otps_teacher ON public.application_otps (teacher_id);

-- RLS on, with NO policies: only the service role (Edge Functions) may access
-- this table; the service role bypasses RLS. No anon or authenticated access.
ALTER TABLE public.application_otps ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.application_otps IS 'Email verification OTPs for teacher applications. Service-role access only. WhatsApp channel reserved for when WhatsApp Business is activated.';

-- 3) WhatsApp "New Teachers" group invite link (config row, not schema) --------
-- Stored in system_config; admin edits the value in Settings. Used to share a
-- join link with provisioned teachers (auto-add is not possible - see design).
INSERT INTO public.system_config (config_key, config_value, description, updated_at, updated_by)
SELECT 'whatsapp_new_teachers_invite_url', '', 'WhatsApp invite link for RITUAL TEACHERS community > New Teachers group. Shared with newly provisioned teachers.', now(), 'migration:2026-06-01-teacher-applications'
WHERE NOT EXISTS (
  SELECT 1 FROM public.system_config WHERE config_key = 'whatsapp_new_teachers_invite_url'
);

COMMIT;

-- VERIFY (run after apply):
--   SELECT column_name FROM information_schema.columns
--     WHERE table_name='teachers' AND column_name IN
--     ('status','experience_training','cv_url','email_verified','possible_duplicate');
--   SELECT count(*) FROM public.teachers WHERE status <> 'active';   -- expect 0 before import
--   SELECT to_regclass('public.application_otps');                   -- not null
--   SELECT config_key FROM public.system_config WHERE config_key='whatsapp_new_teachers_invite_url';
